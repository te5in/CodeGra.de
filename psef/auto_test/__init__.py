import os  # typing: ignore
import abc
import pwd
import sys
import copy
import json
import time
import uuid
import errno
import random
import signal
import typing as t
import datetime
import tempfile
import threading
import traceback
import contextlib
import subprocess
from pathlib import Path
from multiprocessing import Pool, Event, Queue, Manager, context

import lxc  # typing: ignore
import requests
import structlog
import transip.service
from suds import WebFault
from mypy_extensions import TypedDict

import psef
import cg_logger
from cg_timers import timed_code, timed_function

from .. import app, models
from ..helpers import (
    JSONType, RepeatedTimer, defer, between, ensure_on_test_server
)
from ..registry import auto_test_handlers
from ..exceptions import StopRunningStepsException

logger = structlog.get_logger()

OutputCallback = t.Callable[[bytes], None]
URL = t.NewType('URL', str)

_STOP_CONTAINERS = Event()

T = t.TypeVar('T')

Network = t.NewType('Network', t.Tuple[str, t.List[t.Tuple[str, str]]])
UpdateResultFunction = t.Callable[
    ['models.AutoTestStepResultState', t.Dict[str, object]], None]


class CpuCores():
    def __init__(
        self,
        number_of_cores: t.Optional[int] = None,
        make_queue: t.Callable[[int], Queue] = Queue
    ) -> None:
        self._number_of_cores = number_of_cores or _get_amount_cpus()
        self._available_cores: Queue[int] = make_queue(self._number_of_cores)
        for core in range(self._number_of_cores):
            self._available_cores.put(core)

    @contextlib.contextmanager
    def reserved_core(self) -> t.Generator[int, None, None]:
        core = self._available_cores.get()
        try:
            yield core
        finally:
            self._available_cores.put(core)


class StopContainerException(Exception):
    pass


class CommandTimeoutException(Exception):
    def __init__(
        self,
        cmd: str = '',
        stdout: str = '',
        stderr: str = '',
        time_spend: t.Optional[float] = None,
    ) -> None:
        self.cmd = cmd
        self.stdout = stdout
        self.stderr = stderr
        self.time_spend = time_spend


def _maybe_quit_running() -> None:
    if _STOP_CONTAINERS.is_set():
        raise StopContainerException


def _get_new_container_name() -> str:
    return str(uuid.uuid1())


def _get_amount_cpus() -> int:
    return os.cpu_count() or 1


def _get_base_container(config: 'psef.FlaskConfig') -> 'AutoTestContainer':
    ensure_on_test_server()
    template_name = config['AUTO_TEST_TEMPLATE_CONTAINER']
    if template_name is None:
        res = AutoTestContainer(_get_new_container_name(), config)
        res.create()
    else:
        res = AutoTestContainer(template_name, config).clone()
    return res


def _stop_container(cont: lxc.Container) -> None:
    if cont.running:
        with timed_code('stop_container'):
            assert cont.stop()
            assert cont.wait('STOPPED', 3)


def _start_container(
    cont: lxc.Container, check_network: bool = True, always: bool = False
) -> None:
    if not always:
        _maybe_quit_running()

    if cont.running:
        return

    with timed_code('start_container'):
        assert cont.start()
        assert cont.wait('RUNNING', 3)
        if check_network:
            with timed_code('wait_for_network'):
                for _ in range(60):
                    if cont.get_ips():
                        return
                    time.sleep(0.5)
                    if not always:
                        _maybe_quit_running()
                else:
                    raise Exception(f"Couldn't get ip for container {cont}")


class StepInstructions(TypedDict, total=True):
    id: int
    weight: float
    test_type_name: str
    data: 'psef.helpers.JSONType'
    command_time_limit: float


class SuiteInstructions(TypedDict, total=True):
    id: int
    steps: t.List[StepInstructions]
    network_disabled: bool


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
    fixtures: t.List[t.Tuple[str, int]]
    setup_script: str
    heartbeat_interval: int
    run_setup_script: str


def init_app(app: 'psef.PsefFlask') -> None:
    process_config(app.config)


def process_config(config: 'psef.FlaskConfig') -> None:
    res = {}
    for ip, conf in config['__S_AUTO_TEST_HOSTS'].items():
        assert isinstance(conf['password'], str)
        assert isinstance(conf.get('container_url'), (type(None), str))
        res[ip] = {
            'password': conf['password'],
            'container_url': conf.get('container_url', None),
        }
    config['AUTO_TEST_HOSTS'] = res  # type: ignore


def _push_logging(post_log: t.Callable[[JSONType], object]) -> RepeatedTimer:
    logs: t.List[t.Dict[str, object]] = []
    logs_lock = threading.RLock()

    @cg_logger.logger_callback
    def log_line(logger: object, method_name: str, event_dict: str) -> None:
        # DO NOT LOCK HERE AS THIS WILL CREATE DEADLOCKS!!!
        # Locking is also not needed as a list is a threadsafe object.
        json_event = json.loads(event_dict)
        logs.append(json_event)

    def push_logs() -> None:
        logger.info('Pushing logs')
        with logs_lock:
            logs_copy = list(logs)
            if logs_copy:
                post_log(logs_copy)
            del logs[:len(logs_copy)]

    return RepeatedTimer(
        15, push_logs, cleanup=log_line.disable, use_process=False
    )


# This wrapper function is needed for Python multiprocessing
def _run_student(
    cont: 'AutoTestRunner', bc_name: str, cores: CpuCores, result_id: int
) -> None:
    cont.run_student(bc_name, cores, result_id)


def start_polling(config: 'psef.FlaskConfig') -> None:
    items = list(config['AUTO_TEST_HOSTS'].items())
    sleep_time = config['AUTO_TEST_POLL_TIME']
    broker_url = config['AUTO_TEST_BROKER_URL']

    def do_job(cont: 'StartedContainer') -> bool:
        random.shuffle(items)
        for url, url_config in items:
            headers = {
                'CG-Internal-Api-Password': url_config["password"],
            }
            logger.try_unbind('server')
            logger.bind(server=url)
            logger.info('Checking next server')

            try:
                response = requests.get(
                    f'{url}/api/v-internal/auto_tests/',
                    params={
                        'get': 'tests_to_run',
                    },
                    headers=headers
                )
                response.raise_for_status()
            except requests.exceptions.RequestException:
                logger.error('Failed to get server', exc_info=True)
                continue

            if response.status_code == 200:
                data = response.json()
                logger.info('Got test', response=response, json=data)

                logger_service.cancel()

                try:
                    AutoTestRunner(
                        t.cast(URL,
                               url_config.get('container_url') or url), data,
                        url_config['password'], config
                    ).run_test(cont)
                except:
                    logger.error('Error while running tests', exc_info=True)
                return True
            else:
                logger.info('No tests found', response=response)
        return False

    while True:
        logger_service: RepeatedTimer = _push_logging(
            lambda logs: requests.post(
                f'{broker_url}/api/v1/logs/',
                json={
                    'logs': logs
                },
            ).raise_for_status()
        )
        logger_service.start()

        _STOP_CONTAINERS.clear()

        with _get_base_container(config).started_container() as cont:
            cont.run_command(['apt', 'update'])
            cont.run_command(['apt', 'upgrade', '-y'])
            if config['AUTO_TEST_TEMPLATE_CONTAINER'] is None:
                cont.run_command(
                    ['apt', 'install', '-y', 'wget', 'curl', 'unzip']
                )

            while True:
                if do_job(cont):
                    break
                time.sleep(sleep_time)


class StartedContainer:
    _NETWORK_LOCK = threading.Lock()
    _SNAPSHOT_LOCK = threading.Lock()

    def __init__(
        self, container: lxc.Container, name: str, config: 'psef.FlaskConfig'
    ) -> None:
        self._snapshots: t.List[str] = []
        self._dirty = False
        self._container = container
        self._config = config
        self._name = name

    def _stop_container(self) -> None:
        _stop_container(self._container)

    @contextlib.contextmanager
    def stopped_container(self
                          ) -> t.Generator['AutoTestContainer', None, None]:
        self._stop_container()
        try:
            yield AutoTestContainer(self._name, self._config, self._container)
        finally:
            _start_container(self._container, always=True)

    def destroy_snapshots(self) -> None:
        self._stop_container()
        with self._SNAPSHOT_LOCK, timed_code(
            'destroy_snapshots', snapshot_amount=len(self._snapshots)
        ):
            while self._snapshots:
                self._container.snapshot_destroy(self._snapshots.pop())

    def set_cgroup_item(self, key: str, value: str) -> None:
        success = self._container.set_cgroup_item(key, value)
        if not success:
            raise ValueError(f'Could not set "{key}" to "{value}"')

    def _create_snapshot(self) -> None:
        with self._SNAPSHOT_LOCK:
            snap = self._container.snapshot()
            assert isinstance(snap, str)
            self._snapshots.append(snap)
            self._dirty = False

    @timed_function
    def _disable_network(self) -> t.List[Network]:
        self._stop_container()

        with self._NETWORK_LOCK:
            res: t.List[Network] = []
            for network in self._container.network:
                net = (
                    network.type,
                    [(attr, getattr(network, attr)) for attr in dir(network)]
                )
                res.append(Network(net))
            for network_idx in range(len(self._container.network)):
                assert self._container.network.remove(network_idx)

        _start_container(self._container, check_network=False)
        return res

    @timed_function
    def _enable_network(self, networks: t.List[Network]) -> None:
        self._stop_container()

        with self._NETWORK_LOCK:
            for typ, network in networks:
                assert self._container.network.add(typ)

                # -1 index doesn't work, as this isn't a true list
                last_index = len(self._container.network) - 1
                for key, value in network:
                    setattr(self._container.network[last_index], key, value)

        _start_container(self._container, check_network=True)

    @contextlib.contextmanager
    def as_snapshot(self, disable_network: bool = False
                    ) -> t.Generator['StartedContainer', None, None]:
        _maybe_quit_running()

        # NOTE: This code never destroys snapshots, as this logic makes the
        # function way harder to follow. As we keep a dirty flag, only one
        # snapsnot will probably be created.

        try:
            if disable_network:
                networks = self._disable_network()

            if self._dirty or not self._snapshots:
                with timed_code(
                    'create_snapshot',
                    container=self._name,
                    amount_of_snapshots=len(self._snapshots)
                ):
                    self._stop_container()
                    self._create_snapshot()
                    _start_container(
                        self._container, check_network=not disable_network
                    )
            else:
                logger.info(
                    'Snapshot creation not needed',
                    snapshots=self._snapshots,
                    dirty=self._dirty
                )
            yield self
        finally:
            self._stop_container()
            # Creating the snapshot, so we might not have a snapshot
            if self._snapshots:
                with self._SNAPSHOT_LOCK, timed_code('restore_snapshots'):
                    self._container.snapshot_restore(self._snapshots[-1])
                self._dirty = False

            if disable_network:
                self._enable_network(networks)

            _start_container(self._container)

    def _read_fifo(
        self, callback: t.Optional[OutputCallback], fname: str
    ) -> None:
        with open(fname, 'rb') as f:
            while True:
                _maybe_quit_running()
                line = f.readline()
                if not line:
                    return
                if callback is not None:
                    callback(line)

    @property
    def _extra_path(self) -> str:
        return (
            '~/bin/:~/.pyenv/bin/:~/.local/bin:/home/codegrade/.pyenv/bin:'
            '/home/codegrade/.local/bin/:/home/codegrade/bin/'
        )

    def _change_user(self, username: str) -> None:
        pw_record = pwd.getpwnam(username)
        user_uid = pw_record.pw_uid
        user_gid = pw_record.pw_gid

        os.setgid(user_gid)
        os.setuid(user_uid)

    def create_env(self, username: t.Optional[str]) -> t.Dict:
        env = os.environ
        if username is not None:
            pw_record = pwd.getpwnam(username)
            user = username
            home = pw_record.pw_dir
        else:
            user = 'codegrade'
            home = '/home/codegrade/'

        return {
            'PATH': f'{self._extra_path}:/usr/sbin/:/sbin/:{env["PATH"]}',
            'USER': user,
            'LOGUSER': user,
            'HOME': home,
            'DEBIAN_FRONTEND': 'noninteractive',
            'TERM': 'dumb',
            'FIXTURES': '/home/codegrade/fixtures/',
            'STUDENT': '/home/codegrade/student/',
        }

    def _run_command(
        self, cmd_user: t.Tuple[t.List[str], t.Optional[str]]
    ) -> int:
        cmd, user = cmd_user
        env = self.create_env(user)

        def preexec() -> None:
            if user:
                self._change_user(user)

        return subprocess.call(cmd, preexec_fn=preexec, env=env)

    def _run_shell(self, cmd_cwd_user: t.Tuple[str, str, str]) -> int:
        cmd, cwd, user = cmd_cwd_user
        env = self.create_env(user)
        env['PATH'] += '/home/codegrade/student/:/home/codegrade/fixtures/'

        def preexec() -> None:
            self._change_user(user)

        return subprocess.call(
            cmd,
            cwd=cwd,
            preexec_fn=preexec,
            env=env,
            executable='/bin/bash',
            shell=True,
        )

    def run_student_command(
        self,
        cmd: str,
        timeout: float,
        stdin: t.Union[None, bytes, t.BinaryIO] = None,
    ) -> t.Tuple[int, str, str, float]:
        stdout: t.List[bytes] = []
        stderr: t.List[bytes] = []

        user = 'codegrade'
        cwd = '/home/codegrade/student/'
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

        def get_stdout_and_stderr() -> t.List[str]:
            return [
                b''.join(v).decode('utf-8', 'backslashreplace')
                for v in [stdout, stderr]
            ]

        time_spend = 0.0
        try:
            with timed_code('run_student_command') as get_time_spend:
                code = self._run(
                    cmd=(cmd, cwd, user),
                    callback=self._run_shell,
                    stdout=make_add_function(stdout),
                    stderr=make_add_function(stderr),
                    stdin=stdin,
                    check=False,
                    timeout=timeout,
                )
            time_spend = get_time_spend()
        except CommandTimeoutException as e:
            stdout_str, stderr_str = get_stdout_and_stderr()
            raise CommandTimeoutException(
                cmd=cmd,
                stdout=stdout_str,
                stderr=stderr_str,
                time_spend=time_spend,
            )

        stdout_str, stderr_str = get_stdout_and_stderr()
        return code, stdout_str, stderr_str, time_spend

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
            cmd=(cmd, user),
            callback=self._run_command,
            stdout=stdout,
            stderr=stderr,
            stdin=stdin,
            check=check,
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
        timeout: t.Union[None, float, int],
    ) -> int:
        self._dirty = True

        with cg_logger.bound_to_logger(
            cmd=cmd, timeout=timeout
        ), tempfile.TemporaryDirectory(
        ) as output_dir, tempfile.NamedTemporaryFile() as stdin_file, open(
            '/dev/null', 'r'
        ) as dev_null:
            logger.info('Running command')
            local_logger = structlog.threadlocal.as_immutable(logger)

            if isinstance(stdin, bytes):
                os.chmod(stdin_file.name, 0o777)
                stdin_file.write(stdin)
                stdin_file.flush()
                stdin_file.seek(0, 0)
            elif stdin is None:
                stdin_file = dev_null
            else:
                stdin_file = stdin

            stdout_fifo = os.path.join(output_dir, 'stdout')
            os.mkfifo(stdout_fifo)
            stderr_fifo = os.path.join(output_dir, 'stderr')
            os.mkfifo(stderr_fifo)

            def _make_log_function(log_location: str
                                   ) -> t.Callable[[bytes], None]:
                def inner(log_line: bytes) -> None:
                    local_logger.info(
                        'Got output from command',
                        location=log_location,
                        output=log_line
                    )

                return inner

            stdout_thread = threading.Thread(
                target=self._read_fifo,
                args=(stdout or _make_log_function('stdout'), stdout_fifo)
            )
            stderr_thread = threading.Thread(
                target=self._read_fifo,
                args=(stderr or _make_log_function('stderr'), stderr_fifo)
            )
            stdout_thread.start()
            stderr_thread.start()

            # The order is really important here! We first need to close the
            # two fifo files before we join our threads. As otherwise the
            # threads will hang because they are still reading from these
            # files.
            with defer(stdout_thread.join), defer(stderr_thread.join), open(
                stdout_fifo,
                'wb',
            ) as out, open(
                stderr_fifo,
                'wb',
            ) as err:
                assert timeout is None or timeout > 0
                start = datetime.datetime.utcnow()
                _maybe_quit_running()

                pid = self._container.attach(
                    callback,
                    cmd,
                    stdout=out,
                    stderr=err,
                    stdin=stdin_file,
                )

                def get_time_left() -> float:
                    if timeout is None:
                        return sys.maxsize
                    time_spend = datetime.datetime.utcnow() - start
                    return timeout - time_spend.total_seconds()

                def timed_out() -> bool:
                    return get_time_left() < 0

                def get_sleep_time() -> float:
                    return between(0.025, get_time_left() / 4, 0.5)

                while not _STOP_CONTAINERS.is_set() and not timed_out():
                    try:
                        # Make sure pid already exists
                        new_pid, status = os.waitpid(pid, os.WNOHANG)
                        if new_pid == status == 0:
                            time.sleep(get_sleep_time())
                        elif os.WIFEXITED(status):
                            res = os.WEXITSTATUS(status)
                            break
                        elif os.WIFSIGNALED(status) or os.WCOREDUMP(status):
                            logger.warning(
                                'Unusual process exit',
                                pid=pid,
                                new_pid=new_pid,
                                status=status
                            )
                            res = -1
                            break
                        else:
                            logger.warning('Unknown process error!')
                            time.sleep(get_sleep_time())
                    except OSError as e:
                        if e.errno == errno.EINTR:
                            continue
                        raise
                else:
                    logger.warning('Process took too long, killing', pid=pid)
                    os.kill(pid, signal.SIGKILL)
                    os.waitpid(pid, 0)
                    logger.warning('Killing done', pid=pid)
                    _maybe_quit_running()
                    raise CommandTimeoutException

            _maybe_quit_running()

            if check and res != 0:
                raise RuntimeError(f'Command "{cmd}" crashed: {res}')

            return res


class AutoTestContainer:
    def __init__(
        self,
        name: str,
        config: 'psef.FlaskConfig',
        cont: t.Optional[lxc.Container] = None
    ) -> None:
        self._name = name
        self._lock = threading.RLock()
        self._config = config
        if cont is None:
            self._cont = lxc.Container(name)
        else:
            self._cont = cont

    @property
    def name(self) -> str:
        return self._name

    def create(self) -> None:
        assert self._cont.create(
            'download',
            0, {
                'dist': 'ubuntu',
                'release': 'bionic',
                'arch': 'amd64',
            },
            bdevtype=self._config['AUTO_TEST_BDEVTYPE']
        )

    @contextlib.contextmanager
    def started_container(self) -> t.Generator[StartedContainer, None, None]:
        started = None

        try:
            _start_container(self._cont)
            started = StartedContainer(self._cont, self._name, self._config)
            yield started
        finally:
            self._stop_container(started)

    def _stop_container(self, cont: t.Optional[StartedContainer]) -> None:
        with cg_logger.bound_to_logger(cont=self):
            try:
                _stop_container(self._cont)
                if cont is not None:
                    logger.info('Destroying snapshots')
                    cont.destroy_snapshots()
            finally:
                with timed_code('destroy_container'):
                    self._cont.destroy()

    def clone(self, new_name: str = '') -> 'AutoTestContainer':
        _maybe_quit_running()

        new_name = new_name or _get_new_container_name()

        with self._lock, timed_code('clone_container'):
            cont = self._cont.clone(new_name)
            assert isinstance(cont, lxc.Container)
            return type(self)(new_name, self._config, cont)


class AutoTestRunner:
    def __init__(
        self, base_url: URL, instructions: RunnerInstructions,
        global_password: str, config: 'psef.FlaskConfig'
    ) -> None:
        self._global_password = global_password
        self.instructions = instructions
        self.auto_test_id = instructions['auto_test_id']
        self.config = config
        self.setup_script = self.instructions['setup_script']
        self.base_url = (
            f'{base_url}/api/v-internal/auto_tests/{self.auto_test_id}'
        )

        self.fixtures = self.instructions['fixtures']

        self.req = requests.Session()
        self.req.headers.update(
            {
                'CG-Internal-Api-Password': self._global_password,
                'CG-Internal-Api-Runner-Password': self._local_password,
            }
        )

    @property
    def _local_password(self) -> str:
        return self.instructions["runner_id"]

    @property
    def wget_headers(self) -> t.List[str]:
        return [
            '--header',
            f'CG-Internal-Api-Password: {self._global_password}',
            '--header',
            f'CG-Internal-Api-Runner-Password: {self._local_password}',
        ]

    def copy_file(
        self, container: StartedContainer, src: str, dst: str
    ) -> None:
        with open(src, 'rb') as f:
            container.run_command(['dd', 'status=none', f'of={dst}'], stdin=f)
        container.run_command(['chmod', '+x', dst])
        container.run_command(['ls', '-hal', dst])
        container.run_command(['cat', dst])

    def download_fixtures(self, cont: StartedContainer) -> None:
        for name, fixture_id in self.fixtures:
            url = f'{self.base_url}/fixtures/{fixture_id}'
            path = f'/home/codegrade/fixtures/{name}'
            cont.run_command(
                [
                    'wget',
                    *self.wget_headers,
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
        )

    @timed_function
    def download_student_code(
        self, cont: StartedContainer, result_id: int
    ) -> None:
        url = f'{self.base_url}/results/{result_id}?type=submission_files'

        cont.run_command(
            [
                'wget',
                *self.wget_headers,
                url,
                '-O',
                '/home/codegrade/student.zip',
            ],
            user='codegrade'
        )
        logger.info('Downloaded student code', url=url)

        cont.run_command(
            [
                'unzip', '/home/codegrade/student.zip', '-d',
                '/home/codegrade/student/'
            ],
            user='codegrade',
        )
        logger.info('Extracted student code')

        cont.run_command(
            ['chmod', '-R', '+x', '/home/codegrade/student/'],
            user='codegrade'
        )
        cont.run_command(['rm', '-f', '/home/codegrade/student.zip'])

    @timed_function
    def _run_test_suite(
        self, student_container: StartedContainer, result_id: int,
        test_suite: SuiteInstructions
    ) -> float:
        total_points = 0.0

        with student_container.as_snapshot(
            test_suite['network_disabled']
        ) as snap:
            url = f'{self.base_url}/results/{result_id}/step_results/'

            for test_step in test_suite['steps']:
                logger.info('Running step', step=test_step)
                step_result_id: t.Optional[int] = None

                def update_test_result(
                    state: models.AutoTestStepResultState,
                    log: t.Dict[str, object]
                ) -> None:
                    nonlocal step_result_id
                    data = {
                        'log': log,
                        'state': state.name,
                        'auto_test_step_id': test_step['id'],
                    }
                    if step_result_id is not None:
                        data['id'] = step_result_id

                    logger.info('Posting result data', json=data, url=url)
                    response = self.req.put(
                        url,
                        json=data,
                    )
                    logger.info('Posted result data', response=response)
                    assert response.status_code == 200
                    step_result_id = response.json()['id']

                typ = auto_test_handlers[test_step['test_type_name']]

                with timed_code('run_suite_step') as get_step_time:
                    try:
                        logger.bind(step=test_step)
                        total_points += typ.execute_step(
                            test_step['data'], snap, update_test_result,
                            test_step, total_points
                        )
                    except StopRunningStepsException:
                        logger.info('Stopping steps', exc_info=True)
                        break
                    except CommandTimeoutException as e:
                        logger.warning('Command timed out', exc_info=True)
                        update_test_result(
                            models.AutoTestStepResultState.timed_out, {
                                'exit_code': -1,
                                'stdout': e.stdout,
                                'stderr': e.stderr,
                                'time_spend': get_step_time(),
                            }
                        )
                    else:
                        logger.info('Ran step')
                    finally:
                        logger.try_unbind('step')

        return total_points

    @timed_function
    def _run_student(
        self,
        base_container_name: str,
        cpu_cores: CpuCores,
        result_id: int,
    ) -> None:
        base_container = AutoTestContainer(base_container_name, self.config)
        student_container = base_container.clone()

        result_url = f'{self.base_url}/results/{result_id}'
        result_state = models.AutoTestStepResultState.running

        try:
            with student_container.started_container(
            ) as cont, cpu_cores.reserved_core() as cpu_number:
                self.req.patch(result_url, json={'state': result_state.name})

                with timed_code('set_cgroup_limits'):
                    cont.set_cgroup_item(
                        'memory.limit_in_bytes',
                        self.config['AUTO_TEST_MEMORY_LIMIT']
                    )
                    cont.set_cgroup_item('cpuset.cpus', str(cpu_number))
                    cont.set_cgroup_item(
                        'memory.memsw.limit_in_bytes',
                        self.config['AUTO_TEST_MEMORY_LIMIT']
                    )

                self.download_student_code(cont, result_id)

                self._maybe_run_setup(cont, self.setup_script, result_url)

                logger.info('Dropping sudo rights')
                cont.run_command(['deluser', 'codegrade', 'sudo'])
                cont.run_command(
                    ['sed', '-i', 's/^codegrade.*$//g', '/etc/sudoers']
                )
                assert cont.run_command(
                    ['grep', 'codegrade', '/etc/sudoers'], check=False
                ) != 0, "Sudo was not dropped!"

                total_points = 0.0

                for test_set in self.instructions['sets']:
                    for test_suite in test_set['suites']:
                        total_points += self._run_test_suite(
                            cont, result_id, test_suite
                        )
                    if total_points < test_set['stop_points']:
                        break
        except CommandTimeoutException:
            logger.error('Command timed out', exc_info=True)
            result_state = models.AutoTestStepResultState.timed_out
        except:
            logger.error('Something went wrong', exc_info=True)
            result_state = models.AutoTestStepResultState.failed
            raise
        else:
            result_state = models.AutoTestStepResultState.passed
        finally:
            self.req.patch(
                result_url,
                json={'state': result_state.name},
            )

    def run_student(
        self,
        base_container_name: str,
        cpu_cores: CpuCores,
        result_id: int,
    ) -> None:
        with _push_logging(self._push_log
                           ), cg_logger.bound_to_logger(result_id=result_id):
            self._run_student(base_container_name, cpu_cores, result_id)

    def started_heartbeat(self) -> 'RepeatedTimer':
        def push_heartbeat() -> None:
            self.req.post(
                f'{self.base_url}/runs/{self.instructions["run_id"]}/'
                'heartbeats/'
            ).raise_for_status()

        interval = self.instructions['heartbeat_interval']
        logger.info('Starting heartbeat interval', interval=interval)
        return RepeatedTimer(interval, push_heartbeat, use_process=True)

    def _push_log(self, logs: JSONType) -> object:
        return self.req.post(
            f'{self.base_url}/runs/{self.instructions["run_id"]}/logs/',
            json={'logs': logs},
        )

    def run_test(self, cont: StartedContainer) -> None:
        run_result_url = f'{self.base_url}/runs/{self.instructions["run_id"]}'
        time_taken: t.Optional[float] = None
        push_log_timer = _push_logging(self._push_log).start()

        with self.started_heartbeat():
            self.req.patch(
                run_result_url,
                json={'state': models.AutoTestRunState.starting.name},
            )
            try:
                with timed_code('run_complete_auto_test') as get_time_taken:
                    self._run_test(cont)
                time_taken = get_time_taken()
            except:
                end_state = models.AutoTestRunState.crashed.name
                raise
            else:
                logger.info('Finished running tests')
                end_state = models.AutoTestRunState.done.name
            finally:
                try:
                    push_log_timer.cancel()
                finally:
                    self.req.patch(
                        run_result_url,
                        json={
                            'state': end_state,
                            'time_taken': time_taken,
                        },
                    )

    def _maybe_run_setup(
        self, cont: 'StartedContainer', cmd: str, url: str
    ) -> None:
        if cmd:
            with timed_code(
                'run_setup_script', setup_cmd=cmd
            ) as get_time_spend:
                _, stdout, stderr, _ = cont.run_student_command(cmd, 900)

            self.req.patch(
                f'{self.base_url}/runs/{self.instructions["run_id"]}',
                json={
                    'setup_time_spend': get_time_spend(),
                    'setup_stdout': stdout,
                    'setup_stderr': stderr
                },
            )

    def _run_test(self, cont: StartedContainer) -> None:
        ensure_on_test_server()
        with timed_code('install_base_system'):
            cont.run_command(['apt', 'update'])
            cont.run_command(['apt', 'upgrade', '-y'])

        with timed_code('run_setup_commands'):
            cont.run_command(
                [
                    'adduser', '--shell', '/bin/bash', '--disabled-password',
                    '--gecos', '', 'codegrade'
                ],
            )
            cont.run_command(
                ['mkdir', '-p', '/home/codegrade/student/'], user='codegrade'
            )
            cont.run_command(
                ['mkdir', '/home/codegrade/fixtures/'], user='codegrade'
            )

            cont.run_command(['usermod', '-aG', 'sudo', 'codegrade'])

            cont.run_command(
                ['tee', '--append', '/etc/sudoers'],
                stdin=b'\ncodegrade ALL=(ALL) NOPASSWD: ALL\n'
            )
            cont.run_command(['grep', 'codegrade', '/etc/sudoers'])

        with timed_code('download_fixtures'):
            self.download_fixtures(cont)

        self._maybe_run_setup(
            cont,
            self.instructions['run_setup_script'],
            f'{self.base_url}/runs/{self.instructions["run_id"]}',
        )

        self.req.patch(
            f'{self.base_url}/runs/{self.instructions["run_id"]}',
            json={'state': models.AutoTestRunState.running.name},
        )

        with cont.stopped_container() as base_container, timed_code(
            'run_all_students'
        ), Manager() as m, Pool(
            # Over provision a bit so clones can be made quicker.
            _get_amount_cpus() + 4
        ) as pool:
            # Known issue from typeshed:
            # https://github.com/python/typeshed/issues/3018
            make_queue: t.Callable[[int], Queue] = m.Queue  # type: ignore
            cpu_cores = CpuCores(make_queue=make_queue)

            try:
                res = pool.starmap_async(
                    _run_student, [
                        (self, base_container.name, cpu_cores, res_id)
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
            except:
                _STOP_CONTAINERS.set()
                time.sleep(1)

                tracebacks = []
                for th in threading.enumerate():
                    if th.ident is not None:
                        tb = traceback.format_stack(
                            sys._current_frames()[th.ident]
                        )
                        tracebacks.append([th.ident, tb])
                logger.error(
                    'AutoTest crashed',
                    tracebacks=tracebacks,
                    exc_info=True,
                )
                raise
            else:
                logger.info('Done with containers, cleaning up')
                _STOP_CONTAINERS.set()
