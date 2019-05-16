import os  # typing: ignore
import abc
import pwd
import sys
import copy
import json
import time
import uuid
import errno
import signal
import typing as t
import datetime
import tempfile
import threading
import contextlib
import subprocess
from multiprocessing import Queue, context
from multiprocessing.dummy import Pool

import lxc  # typing: ignore
import requests
import structlog
from mypy_extensions import TypedDict

import psef

from .. import app
from .steps import TestStep, StopRunningStepsException, auto_test_handlers
from ..helpers import register, ensure_on_test_server

logger = structlog.get_logger()

auto_test_runners: register.Register[str, t.Type['AutoTestRunner']
                                     ] = register.Register()

OutputCallback = t.Callable[[bytes], None]
URL = t.NewType('URL', str)

STOP_CONTAINERS = threading.Event()

T = t.TypeVar('T')


def get_new_container_name() -> str:
    return str(uuid.uuid1())


def get_amount_cpus() -> int:
    return os.cpu_count() or 1


def _start_container(cont: lxc.Container) -> None:
    cont.start()
    cont.wait('RUNNING', 3)
    for _ in range(30):
        if cont.get_ips():
            return
        time.sleep(1)
    else:
        raise Exception(f"Couldn't get ip for container {cont}")


class StepInstructions(TypedDict, total=True):
    id: int
    weight: float
    test_type_name: str
    data: 'psef.helpers.JSONType'


class SuiteInstructions(TypedDict, total=True):
    id: int
    steps: t.List[StepInstructions]


class SetInstructions(TypedDict, total=True):
    id: int
    suites: t.List[SuiteInstructions]
    stop_points: float


class RunnerInstructions(TypedDict, total=True):
    runner_id: str
    run_id: int
    auto_test_id: int
    result_ids: t.List[int]
    sets: t.List[SetInstructions]
    base_systems: t.List[t.Dict[str, str]]
    fixtures: t.List[t.Tuple[str, int]]
    setup_script: str


def init_app(app: 'psef.PsefFlask') -> None:
    res = {}
    for ip, conf in app.config['__S_AUTO_TEST_CREDENTIALS'].items():
        assert isinstance(conf['password'], str)
        assert isinstance(conf['type'], str)
        typ = auto_test_runners[conf['type']]
        res[ip] = {
            'password': conf['password'],
            'type': typ,
            'disable_origin_check': conf.get('disable_origin_check', False),
        }
    app.config['AUTO_TEST_CREDENTIALS'] = res  # type: ignore


def start_polling(config: 'psef.FlaskConfig') -> None:
    while True:
        for url, url_config in config['__S_AUTO_TEST_CREDENTIALS'].items():
            logger.try_unbind('server')
            logger.bind(server=url)
            logger.info('Checking next server')

            try:
                response = requests.get(
                    f'{url}/api/v-internal/auto_tests/',
                    params={
                        'get': 'tests_to_run',
                    },
                    headers={
                        'CG-Internal-Api-Password':
                            f'{url_config["password"]}@:@',
                    }
                )
            except requests.exceptions.RequestException:
                logger.error('Failed to get server', exc_info=True)
                continue

            if response.status_code == 200:
                data = response.json()
                logger.info('Got test', response=response, json=data)
                typ = auto_test_runners[url_config['type']]
                typ(
                    t.cast(URL,
                           url_config.get('container_url') or url), data,
                    url_config['password'], config
                ).run_test()
                break
            else:
                logger.info('No tests found', response=response)
                continue
        else:
            sleep_time = config['AUTO_TEST_POLL_TIME']
            logger.info('Tried all servers, sleeping', sleep_time=sleep_time)
            time.sleep(sleep_time)

        logger.try_unbind('server')


class StartedContainer:
    def __init__(
        self, container: lxc.Container, config: 'psef.FlaskConfig'
    ) -> None:
        self._snapshots: t.List[str] = []
        self._dirty = False
        self._container = container
        self._config = config

    def destroy_snapshots(self) -> None:
        self.stop_container()
        while self._snapshots:
            self._container.snapshot_destroy(self._snapshots.pop())

    def set_cgroup_item(self, key: str, value: str) -> bool:
        return self._container.set_cgroup_item(key, value)

    def stop_container(self) -> None:
        self._container.stop()
        self._container.wait('STOPPED', 3)

    @contextlib.contextmanager
    def as_snapshot(self) -> t.Generator['StartedContainer', None, None]:
        pop_later = False

        if STOP_CONTAINERS.is_set():
            raise Exception

        try:
            if self._dirty or not self._snapshots:
                pop_later = bool(self._snapshots)
                self.stop_container()
                snap = self._container.snapshot()
                assert isinstance(snap, str)
                self._snapshots.append(snap)
                _start_container(self._container)
                self._dirty = False
            yield self
        finally:
            logger.info('Stopping container')
            self.stop_container()
            if self._snapshots:
                logger.info('Restoring snapshots')
                self._container.snapshot_restore(self._snapshots[-1])
                if pop_later:
                    self._container.snapshot_destroy(self._snapshots.pop())
            _start_container(self._container)
            self._dirty = False

    def _read_fifo(
        self, callback: t.Optional[OutputCallback], fname: str
    ) -> None:
        with open(fname, 'rb') as f:
            while True:
                line = f.readline()
                if not line:
                    return
                if callback is not None:
                    callback(line)

    def _change_user(self, username: str) -> None:
        pw_record = pwd.getpwnam(username)
        user_uid = pw_record.pw_uid
        user_gid = pw_record.pw_gid
        os.environ['USER'] = username
        os.setgid(user_gid)
        os.setuid(user_uid)

    def _run_command(
        self, cmd_user: t.Tuple[t.List[str], t.Optional[str]]
    ) -> int:
        cmd, user = cmd_user
        env = os.environ.copy()
        env['PATH'] += ':/usr/sbin/:/sbin/'

        def preexec() -> None:
            if user:
                self._change_user(user)

        return subprocess.call(cmd, preexec_fn=preexec, env=env)

    def _run_shell(self, cmd_cwd_user: t.Tuple[str, str, str]) -> int:
        cmd, cwd, user = cmd_cwd_user
        env = os.environ.copy()
        env['PATH'] += ':/home/codegrade/student/:/home/codegrade/fixtures/'

        def preexec() -> None:
            self._change_user(user)

        return subprocess.call(
            cmd, shell=True, cwd=cwd, preexec_fn=preexec, env=env
        )

    def run_student_command(
        self,
        cmd: str,
        stdin: t.Union[None, bytes, t.BinaryIO] = None,
    ) -> t.Tuple[int, str, str]:
        stdout: t.List[bytes] = []
        stderr: t.List[bytes] = []

        user = 'codegrade'
        cwd = '/home/codegrade/student/'
        timeout = self._config['AUTO_TEST_MAX_TIME_SINGLE_RUN']
        assert timeout > 0
        max_size = self._config['AUTO_TEST_OUTPUT_LIMIT']
        assert max_size > 0

        size_lock = threading.RLock()
        total_size = 0

        def make_add_function(lst: t.List[bytes]) -> t.Callable[[bytes], None]:
            if max_size is None:
                return lst.append
            else:

                def fun(data: bytes) -> None:
                    nonlocal total_size
                    assert max_size is not None
                    with size_lock:
                        if total_size >= max_size:
                            return
                        size_left = max_size - total_size
                        if len(data) > size_left:
                            lst.append(data[:size_left])
                            lst.append(b' <OUTPUT TRUNCATED>\n')
                        else:
                            lst.append(data)
                        total_size += len(data)

                return fun

        code = self._run(
            cmd=(cmd, cwd, user),
            callback=self._run_shell,
            stdout=make_add_function(stdout),
            stderr=make_add_function(stderr),
            stdin=stdin,
            check=False,
            timeout=timeout,
        )

        stdout_str, stderr_str = [
            b''.join(v).decode('utf-8', 'backslashreplace')
            for v in [stdout, stderr]
        ]
        return code, stdout_str, stderr_str

    def run_command(
        self,
        cmd: t.List[str],
        stdout: t.Optional[OutputCallback] = None,
        stderr: t.Optional[OutputCallback] = None,
        stdin: t.Union[None, bytes, t.BinaryIO] = None,
        user: t.Optional[str] = None,
        check: bool = True,
    ) -> int:
        return self._run(
            (cmd, user),
            self._run_command,
            stdout,
            stderr,
            stdin,
            check,
            timeout=None
        )

    def _run(
        self,
        cmd: T,
        callback: t.Callable[[T], int],
        stdout: t.Optional[OutputCallback],
        stderr: t.Optional[OutputCallback],
        stdin: t.Union[None, bytes, t.BinaryIO],
        check: bool,
        timeout: t.Optional[int],
    ) -> int:
        self._dirty = True

        with tempfile.TemporaryDirectory(
        ) as output_dir, tempfile.NamedTemporaryFile() as stdin_file:
            if isinstance(stdin, bytes):
                os.chmod(stdin_file.name, 0o777)
                stdin_file.write(stdin)
                stdin_file.flush()
            elif stdin is not None:
                stdin_file = stdin

            stdout_fifo = os.path.join(output_dir, 'stdout')
            os.mkfifo(stdout_fifo)
            stderr_fifo = os.path.join(output_dir, 'stderr')
            os.mkfifo(stderr_fifo)

            stdout_thread = threading.Thread(
                target=self._read_fifo, args=(stdout, stdout_fifo)
            )
            stderr_thread = threading.Thread(
                target=self._read_fifo, args=(stderr, stderr_fifo)
            )
            stdout_thread.start()
            stderr_thread.start()

            with open(stdout_fifo,
                      'wb') as out, open(stderr_fifo, 'wb') as err:
                assert timeout is None or timeout > 0
                start = datetime.datetime.utcnow()
                if STOP_CONTAINERS.is_set():
                    raise Exception

                pid = self._container.attach(
                    callback,
                    cmd,
                    stdout=out,
                    stderr=err,
                    stdin=stdin_file,
                )
                while not STOP_CONTAINERS.is_set() and (
                    timeout is None or
                    (datetime.datetime.utcnow() - start).total_seconds() <
                    timeout
                ):
                    try:
                        new_pid, status = os.waitpid(pid, os.WNOHANG)
                        if new_pid == status == 0 or not os.WIFEXITED(status):
                            time.sleep(6)
                            continue
                        res = os.WEXITSTATUS(status)
                        break
                    except OSError as e:
                        if e.errno == errno.EINTR:
                            continue
                        raise
                else:
                    logger.warning('Process took too long, killing', pid=pid)
                    os.kill(pid, signal.SIGKILL)
                    os.waitpid(pid, 0)
                    logger.warning('Killing done', pid=pid)
                    if STOP_CONTAINERS.is_set():
                        raise Exception
                    return -1
                if STOP_CONTAINERS.is_set():
                    raise Exception

            stdout_thread.join()
            stderr_thread.join()

            if check and res != 0:
                raise RuntimeError(f'Command "{cmd}" crashed: {res}')

            return res


if t.TYPE_CHECKING:

    class Container:
        running: bool

        def __init__(self, name: str) -> None:
            ...

        def stop(self) -> None:
            ...

        def wait(self, state: str, time: int) -> None:
            ...

        def destroy(self) -> None:
            ...

        def start(self) -> None:
            ...

        def get_ips(self) -> t.List[object]:
            ...

        def clone(self, name: str) -> 'Container':
            ...

        def create(self, *args: object, **kwargs: object) -> None:
            ...
else:
    Container = lxc.Container


class AutoTestContainer(Container):
    def __init__(self, name: str, config: 'psef.FlaskConfig') -> None:
        super().__init__(name)
        self._lock = threading.RLock()
        self._config = config

    @contextlib.contextmanager
    def started_container(self) -> t.Generator[StartedContainer, None, None]:
        self._start_container()
        started = None
        try:
            started = StartedContainer(self, self._config)
            yield started
        finally:
            self._stop_container(started)

    def _stop_container(self, cont: t.Optional[StartedContainer]) -> None:
        logger.info('Stopping container', cont=self)
        try:
            if self.running:
                self.stop()
                self.wait('STOPPED', 3)
            if cont is not None:
                logger.info('Destroying snapshots')
                cont.destroy_snapshots()
        finally:
            logger.info('Destroying container')
            try:
                self.destroy()
            finally:
                logger.try_unbind('cont')

    def _start_container(self) -> None:
        self.start()
        self.wait('RUNNING', 3)
        for _ in range(30):
            if self.get_ips():
                break
            time.sleep(1)
        else:
            raise Exception(f"Couldn't get ip for container {self}")

    def clone(self, new_name: str = '') -> 'AutoTestContainer':
        if STOP_CONTAINERS.is_set():
            raise Exception

        with self._lock:
            res = super().clone(new_name or get_new_container_name())
            assert isinstance(res, lxc.Container)
            res.__class__ = type(self)
            res._lock = threading.RLock()
            res._config = self._config
            return res


class AutoTestRunner(abc.ABC):
    def __init__(
        self, base_url: URL, instructions: RunnerInstructions,
        global_password: str, config: 'psef.FlaskConfig'
    ) -> None:
        self.base_url = base_url
        self._global_password = global_password
        self.instructions = instructions
        self.auto_test_id = instructions['auto_test_id']
        self.config = config
        self.setup_script = self.instructions['setup_script']

        with open(
            os.path.join(
                os.path.dirname(__file__), '..', '..', 'seed_data',
                'auto_test_base_systems.json'
            ), 'r'
        ) as f:
            self.base_systems = [
                val for val in json.load(f)
                if val['id'] in self.instructions['base_systems']
            ]
        self.fixtures = self.instructions['fixtures']

    @property
    def password(self) -> str:
        return f'{self._global_password}@:@{self.instructions["runner_id"]}'

    @abc.abstractmethod
    def run_test(self) -> None:
        ...

    @classmethod
    @abc.abstractmethod
    def after_run(cls, runner: 'psef.models.AutoTestRunner') -> None:
        pass

    def make_container(self) -> AutoTestContainer:
        return AutoTestContainer(get_new_container_name(), self.config)


@auto_test_runners.register('simple_runner')
class _SimpleAutoTestRunner(AutoTestRunner):
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self._init_log: t.List[bytes] = []

    @classmethod
    def after_run(_, __: 'psef.models.AutoTestRunner') -> None:
        pass

    def _install_base_systems(self, cont: StartedContainer) -> None:
        for system in self.base_systems:
            for cmd in system['setup_commands']:
                print(cont.run_command(cmd))

    def _finalize_base_systems(self, cont: StartedContainer) -> None:
        for system in self.base_systems:
            for cmd in system.get('pre_start_commands', []):
                print(
                    cont.run_command(
                        cmd, self._init_log.append, self._init_log.append
                    )
                )

    def copy_file(
        self, container: StartedContainer, src: str, dst: str
    ) -> None:
        with open(src, 'rb') as f:
            container.run_command(
                ['dd', 'status=none', f'of={dst}'],
                self._init_log.append,
                self._init_log.append,
                stdin=f
            )
        container.run_command(
            ['chmod', '+x', dst], self._init_log.append, self._init_log.append
        )

    def download_fixtures(self, cont: StartedContainer) -> None:
        cont.run_command(
            ['mkdir', '/home/codegrade/fixtures/'], user='codegrade'
        )

        for name, fixture_id in self.fixtures:
            url = (
                f'{self.base_url}/api/v-internal/auto_tests/'
                f'{self.auto_test_id}/fixtures/{fixture_id}'
            )
            path = f'/home/codegrade/fixtures/{name}'
            cont.run_command(
                [
                    'wget',
                    '--header',
                    f'CG-Internal-Api-Password: {self.password}',
                    url,
                    '-O',
                    path,
                ],
                user='codegrade'
            )
            logger.info('Downloaded fixtures', name=name, url=url)

        cont.run_command(
            ['chmod', '-R', '+x', '/home/codegrade/fixtures/'],
            user='codegrade'
        )
        cont.run_command(
            ['ls', '-hl', '/home/codegrade/fixtures/'],
            user='codegrade',
            stdout=self._init_log.append,
            stderr=self._init_log.append,
        )

    def download_student_code(
        self, cont: StartedContainer, result_id: int
    ) -> None:
        url = (
            f'{self.base_url}/api/v-internal/auto_tests/'
            f'{self.auto_test_id}/results/{result_id}?type=submission_files'
        )

        logger.info('Downloading student code', url=url)
        cont.run_command(
            [
                'wget',
                f'--header=CG-Internal-Api-Password: {self.password}',
                url,
                '-O',
                '/home/codegrade/student.zip',
            ],
            user='codegrade'
        )
        logger.info('Downloaded student code', url=url)

        cont.run_command(
            ['mkdir', '-p', '/home/codegrade/student/'], user='codegrade'
        )
        cont.run_command(
            [
                'unzip', '/home/codegrade/student.zip', '-d',
                '/home/codegrade/student/'
            ],
            user='codegrade'
        )
        logger.info('Extracted student code')

        cont.run_command(
            ['chmod', '-R', '+x', '/home/codegrade/student/'],
            user='codegrade'
        )
        cont.run_command(
            ['rm', '-f', '/home/codegrade/student.zip'], user='codegrade'
        )

    def run_student(
        self,
        base_container: AutoTestContainer,
        cpu_queue: 'Queue[int]',
        result_id: int,
    ) -> None:
        student_container = base_container.clone()
        cpu_number = cpu_queue.get()

        try:
            logger.bind(result_id=result_id)
            logger.info('Starting container for student')
            with student_container.started_container() as cont:
                logger.info('Started container')
                logger.info('Setting limits')
                assert cont.set_cgroup_item(
                    'memory.limit_in_bytes',
                    self.config['AUTO_TEST_MEMORY_LIMIT']
                )
                assert cont.set_cgroup_item('cpuset.cpus', str(cpu_number))
                assert cont.set_cgroup_item(
                    'memory.memsw.limit_in_bytes',
                    self.config['AUTO_TEST_MEMORY_LIMIT']
                )
                logger.info('Done setting limits')

                self.download_student_code(cont, result_id)

                if self.setup_script:
                    logger.info('Running setup script')
                    cont.run_student_command(self.setup_script)

                logger.info('Dropping sudo rights')
                cont.run_command(['deluser', 'codegrade', 'sudo'])

                for test_set in self.instructions['sets']:
                    for test_suite in test_set['suites']:
                        logger.info(
                            'Creating snapshot',
                            test_set=test_set,
                            test_suite=test_suite
                        )

                        with cont.as_snapshot() as snap:
                            url = (
                                f'{self.base_url}/api/v-internal/auto_tests/'
                                f'{self.auto_test_id}/results/{result_id}/'
                                f'step_results/'
                            )

                            for test_step in test_suite['steps']:
                                logger.info('Running step', step=test_step)
                                step_result_id: t.Optional[int] = None

                                def update_test_result(
                                    state: psef.models.AutoTestStepResultState,
                                    log: t.Dict[str, object]
                                ) -> None:
                                    nonlocal step_result_id
                                    data: t.Dict[str, object] = {}
                                    data['auto_test_step_id'] = test_step['id']
                                    if step_result_id is not None:
                                        data['id'] = step_result_id
                                    data['log'] = log
                                    data['state'] = state.name

                                    logger.info('Posting result data')
                                    response = requests.put(
                                        url,
                                        json=data,
                                        headers={
                                            'CG-Internal-Api-Password':
                                                self.password
                                        }
                                    )
                                    logger.info(
                                        'Posted result data',
                                        response=response
                                    )
                                    assert response.status_code == 200
                                    step_result_id = response.json()['id']

                                typ = auto_test_handlers[
                                    test_step['test_type_name']]
                                try:
                                    typ(
                                        test_step['data']
                                    ).execute_step(snap, update_test_result)
                                except StopRunningStepsException:
                                    logger.info('Stopping steps')
                                    break
                                logger.info('Ran step')
        except:
            logger.error('Something went wrong', exc_info=True)
            raise
        finally:
            logger.try_unbind('result_id')
            cpu_queue.put(cpu_number)

    def run_test(self) -> None:
        try:
            self._run_test()
        finally:
            print(b''.join(self._init_log).decode('utf-8', 'backslashreplace'))

    def _run_test(self) -> None:
        # ensure_on_test_server()

        # We use uuid1 as this is always unique for a single machine
        base_container = self.make_container()
        base_container.create(
            'download',
            0, {
                'dist': 'ubuntu',
                'release': 'bionic',
                'arch': 'amd64',
            },
            bdevtype='best'
        )

        with base_container.started_container() as cont:
            cont.run_command(
                ['apt', 'update'], self._init_log.append, self._init_log.append
            )
            cont.run_command(
                ['apt', 'upgrade', '-y'], self._init_log.append,
                self._init_log.append
            )

            # Install useful commands
            cont.run_command(
                ['apt', 'install', '-y', 'wget', 'curl', 'unzip'],
                self._init_log.append, self._init_log.append
            )

            self.copy_file(
                cont,
                (
                    f'{os.path.dirname(__file__)}/'
                    '../../seed_data/install_pyenv.sh'
                ),
                '/usr/bin/install_pyenv.sh',
            )

            self._install_base_systems(cont)

            cont.run_command(
                ['adduser', '--disabled-password', '--gecos', '', 'codegrade'],
                self._init_log.append, self._init_log.append
            )

            cont.run_command(
                ['usermod', '-aG', 'sudo', 'codegrade'], self._init_log.append,
                self._init_log.append
            )

            self.download_fixtures(cont)
            self._finalize_base_systems(cont)

            cont.stop_container()
            del cont

            STOP_CONTAINERS.clear()
            with Pool(get_amount_cpus()) as pool:
                q: 'Queue[int]' = Queue(maxsize=get_amount_cpus())
                for i in range(get_amount_cpus()):
                    q.put(i)

                try:
                    res = pool.starmap_async(
                        self.run_student, [
                            (base_container, q, res_id)
                            for res_id in self.instructions['result_ids']
                        ]
                    )
                    while True:
                        try:
                            res.get(60)
                        except context.TimeoutError:
                            continue
                        else:
                            break
                finally:
                    logger.warning('Got keyboard interrupt, cleaning up')
                    STOP_CONTAINERS.set()
                    pool.terminate()
                    pool.join()
