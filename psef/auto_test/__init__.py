"""This module contains all functionality needed to do an actual AutoTest run.

SPDX-License-Identifier: AGPL-3.0-only
"""
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
import select
import signal
import typing as t
import datetime
import tempfile
import threading
import contextlib
import multiprocessing
from pathlib import Path
from multiprocessing import Event, Queue, Manager, context

import lxc  # typing: ignore
import requests
import structlog
from mypy_extensions import TypedDict

import psef
import cg_logger
from cg_timers import timed_code, timed_function

from .. import models, helpers
from ..helpers import JSONType, RepeatedTimer, defer
from ..registry import auto_test_handlers
from ..exceptions import StopRunningStepsException

logger = structlog.get_logger()

OutputCallback = t.Callable[[bytes], None]
URL = t.NewType('URL', str)

_STOP_CONTAINERS = Event()

T = t.TypeVar('T')
Y = t.TypeVar('Y')

Network = t.NewType('Network', t.Tuple[str, t.List[t.Tuple[str, str]]])
UpdateResultFunction = t.Callable[
    ['models.AutoTestStepResultState', t.Dict[str, object]], None]

CODEGRADE_USER = 'codegrade'


class LXCProcessError(Exception):
    pass


def _get_home_dir(name: str) -> str:
    """Get the home dir of the given user

    >>> _get_home_dir('height')
    '/home/height'
    >>> _get_home_dir(CODEGRADE_USER)
    '/home/codegrade'
    """
    return f'/home/{name}'


def _wait_for_pid(pid: int, timeout: float) -> t.Tuple[int, float]:
    """Wait for ``pid`` at most ``timeout`` amount of seconds.

    >>> from subprocess import Popen
    >>> p = Popen('sleep 5', shell=True)
    >>> _wait_for_pid(p.pid, 0.25)
    Traceback (most recent call last):
    ...
    CommandTimeoutException
    >>> p.poll() is not None
    True

    It also works when SIGTERM is ignored.
    >>> p = Popen("trap 'echo SIGTERM!' 15 ; sleep 5", shell=True)
    >>> _wait_for_pid(p.pid, 0.25)
    Traceback (most recent call last):
    ...
    CommandTimeoutException

    >>> pid = Popen('exit 32', shell=True).pid
    >>> time.sleep(0.1)
    >>> _wait_for_pid(pid, 4)[0]
    32

    >>> _wait_for_pid(Popen('exit 20', shell=True).pid, 4)[0]
    20

    >>> exit, left = _wait_for_pid(Popen(['sleep', '0.25']).pid, 1)
    >>> exit
    0
    >>> abs((1 - left) - 0.25) <= 0.05  # Waiting should be fairly accurate
    True

    >>> import doctest
    >>> doctest.ELLIPSIS_MARKER = '-etc-'
    >>> p = Popen('kill -11 $$', shell=True)  # This segfaults
    >>> _wait_for_pid(p.pid, 1)[0] == -1
    -etc-Unusual process exit-etc-
    True
    """
    start_time = time.time()

    def get_time_left() -> float:
        time_spend = time.time() - start_time
        return timeout - time_spend

    def timed_out() -> bool:
        return get_time_left() < 0

    # This timeout delay code is very similar to that of the timeout
    # implementation of `subprocess`. It could probably be improved, but I'm
    # pretty happy with it for now.
    delay = 0.0005

    while not timed_out():
        new_pid, status = os.waitpid(pid, os.WNOHANG)

        if new_pid == status == 0:
            delay = min(delay * 2, get_time_left(), 0.05)
            time.sleep(delay)
        elif os.WIFEXITED(status):
            return os.WEXITSTATUS(status), get_time_left()
        elif os.WIFSIGNALED(status):
            logger.warning(
                'Unusual process exit',
                pid=pid,
                new_pid=new_pid,
                status=status
            )
            return -1, get_time_left()
        else:
            # This should not be possible, as either the process should either
            # not be exited (new_pid == status == 0), or should exit normally
            # (os.WIFEXITED), or it exited through a signal (os.WIFSIGNALED).
            assert False

    logger.warning('Process took too long, killing', pid=pid)
    os.kill(pid, signal.SIGTERM)
    for _ in range(10):
        new_pid, status = os.waitpid(pid, os.WNOHANG)
        if new_pid == status == 0:
            time.sleep(0.1)
        else:
            break
    else:
        logger.warning(
            'Process did not listen to SIGTERM, killing the hard way', pid=pid
        )
        os.kill(pid, signal.SIGKILL)
        os.waitpid(pid, 0)

    _maybe_quit_running()
    end_time = time.time()
    logger.warning('Killing done', pid=pid)
    raise CommandTimeoutException(end_time - start_time)


class LockableValue(t.Generic[T]):
    """This class essentially contains a lock and a value.

    It forces you to acquire the lock before you can get or set the value.
    """

    class _InnerValue(t.Generic[Y]):
        def __init__(self, value: Y) -> None:
            self.value = value

    def __init__(self, initial_value: T) -> None:
        self.__lock = threading.Lock()
        self.__inner_value: 'LockableValue._InnerValue[T]'
        self.__value = initial_value

    def get(self) -> T:
        """Get the internal value.
        """
        with self.__lock:
            return self.__value

    def set(self, value: T) -> None:
        """Set the internal value.
        """
        with self.__lock:
            self.__value = value

    def __enter__(self) -> 'LockableValue._InnerValue[T]':
        self.__lock.acquire()
        self.__inner_value = LockableValue._InnerValue(self.__value)
        return self.__inner_value

    def __exit__(
        self, exc_type: object, exc_value: object, traceback: object
    ) -> None:
        self.__value = self.__inner_value.value
        del self.__inner_value
        self.__lock.release()


class CpuCores():
    """This class contains a reservation system for cpu cores.

    With this class you can make sure only one of the containers is using
    specific core at any specific moment. This also works across multiple
    processes.
    """

    def __init__(
        self,
        number_of_cores: t.Optional[int] = None,
        make_queue: t.Callable[[int], Queue] = Queue
    ) -> None:
        self._number_of_cores = number_of_cores or _get_amount_cpus()
        self._available_cores: 'Queue[int]' = make_queue(self._number_of_cores)
        for core in range(self._number_of_cores):
            self._available_cores.put(core)

    @contextlib.contextmanager
    def reserved_core(self) -> t.Generator[int, None, None]:
        """Reserve a core for the duration of the ``with`` block.
        """
        core = self._available_cores.get()
        try:
            yield core
        finally:
            self._available_cores.put(core)


class StopContainerException(Exception):
    """This exception should be raised by each container when they should stop
    running.
    """


class CommandTimeoutException(Exception):
    """This exception is raised when a command takes too much time.
    """

    def __init__(
        self,
        time_spend: float,
        cmd: str = '',
        stdout: str = '',
        stderr: str = '',
    ) -> None:
        super().__init__()

        self.cmd = cmd
        self.stdout = stdout
        self.stderr = stderr
        self.time_spend = time_spend


def _maybe_quit_running() -> None:
    """Throw appropriate exception if container should stop running.

    >>> _STOP_CONTAINERS.clear()
    >>> _maybe_quit_running() is None
    True
    >>> _STOP_CONTAINERS.set()
    >>> _maybe_quit_running()
    Traceback (most recent call last):
    ...
    StopContainerException
    >>> _STOP_CONTAINERS.clear()
    >>> _maybe_quit_running() is None
    True
    """
    if _STOP_CONTAINERS.is_set():
        raise StopContainerException


def _get_new_container_name() -> str:
    """Get a new unique container name

    >>> a = _get_new_container_name()
    >>> b = _get_new_container_name()
    >>> type(a)
    <class 'str'>
    >>> a != b
    True
    """
    return str(uuid.uuid1())


def _get_amount_cpus() -> int:
    """Get the amount of cpus on this system or 1 if we cannot detect it.

    This will always be higher than 0.

    >>> _get_amount_cpus() > 0
    True
    """
    return os.cpu_count() or 1


def _get_base_container(config: 'psef.FlaskConfig') -> 'AutoTestContainer':
    helpers.ensure_on_test_server()
    template_name = config['AUTO_TEST_TEMPLATE_CONTAINER']
    if template_name is None:
        logger.info('No base template set, creating new container')
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

                def callback(domain: str) -> int:
                    os.execvp('ping', ['ping', '-w', '1', '-c', '1', domain])
                    assert False

                for _ in helpers.retry_loop(60, sleep_time=0.5):
                    if not always:
                        _maybe_quit_running()

                    if not cont.get_ips():
                        continue

                    for domain in ['codegra.de', 'docs.codegra.de']:
                        if cont.attach_wait(callback, domain) == 0:
                            return


class StepInstructions(TypedDict, total=True):
    """Instructions on how to run a single AutoTest step.

    :ivar id: The id of the step.
    :ivar weight: The amount of points you can achieve with this step.
    :ivar test_type_name: The type of step this is.
    :ivar data: The data of this step, this contains stuff like which command
        to run and what output to expect.
    :ivar command_time_limit: What is the maximum amount of time a command may
        run in this step.
    """
    id: int
    weight: float
    test_type_name: str
    data: 'psef.helpers.JSONType'
    command_time_limit: float


class SuiteInstructions(TypedDict, total=True):
    """Instructions on how to run a single AutoTest suite.

    :ivar id: The id of the suite.
    :ivar steps: The steps of this suite.
    :ivar network_disabled: Should this suite be run with networking disabled.
    """
    id: int
    steps: t.List[StepInstructions]
    network_disabled: bool


class SetInstructions(TypedDict, total=True):
    """Instructions for a single AutoTest set.

    :ivar id: The id of this set.
    :ivar suites: The suites of this set.
    :ivar stop_points: The minimum amount of points that we should have to be
        able to continue running sets.
    """
    id: int
    suites: t.List[SuiteInstructions]
    stop_points: float


class RunnerInstructions(TypedDict, total=True):
    """Instructions for a complete auto test run.

    :ivar runner_id: The id of this runner.
    :ivar run_id: The id of this auto test run.
    :ivar auto_test_id: The id of this AutoTest configuration.
    :ivar result_ids: The ids of the results this runner should produce. These
        can be seen as submissions.
    :ivar sets: The sets that this AutoTest configuration contain.
    :ivar setup_script: The setup script that should be run for each student.
    :ivar run_setup_script: The setup script that should be run once.
    :ivar heartbeat_interval: The interval in seconds to send heartbeats in.
    :ivar fixtures: A list of tuples where the first item is the name of the
        fixture and the second item is its id.
    """
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
    """Process the AutoTest hosts config to the correct format.

    :param config: The configuration that should be processed. This will be
        modified in-place.
    """
    res = {}
    for ipaddr, conf in config['__S_AUTO_TEST_HOSTS'].items():
        assert isinstance(conf['password'], str)
        assert isinstance(conf.get('container_url'), (type(None), str))
        res[ipaddr] = {
            'password': conf['password'],
            'container_url': conf.get('container_url', None),
        }
    config['AUTO_TEST_HOSTS'] = res  # type: ignore


def _push_logging(post_log: t.Callable[[JSONType], object]) -> RepeatedTimer:
    logs: t.List[t.Dict[str, object]] = []
    logs_lock = threading.RLock()

    @cg_logger.logger_callback
    def log_line(_: object, __: str, event_dict: str) -> None:
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


def start_polling(config: 'psef.FlaskConfig', repeat: bool = True) -> None:
    """Start polling the configured CodeGrade instances.

    :param config: The config of this AutoTest runner. This also determines
        what servers will be polled.
    :param repeat: Should we repeat the polling after running a single test.
    """
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
                logger.info(
                    'Got test',
                    response=response,
                    auto_test_id=data.get('auto_test_id')
                )

                logger_service.cancel()

                try:
                    AutoTestRunner(
                        URL(url_config.get('container_url') or url), data,
                        url_config['password'], config
                    ).run_test(cont)
                except:  # pylint: disable=bare-except
                    logger.error('Error while running tests', exc_info=True)
                return True
            else:
                logger.info('No tests found', response=response)
        return False

    first = True
    while first or repeat:
        first = False
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
            if config['AUTO_TEST_TEMPLATE_CONTAINER'] is None:
                cont.run_command(
                    ['apt', 'install', '-y', 'wget', 'curl', 'unzip'],
                    retry_amount=4,
                )

            while True:
                if do_job(cont):
                    break
                time.sleep(sleep_time)
    logger_service.cancel()


class StartedContainer:
    """This class represents a started lxc container. It can be used to execute
    commands.
    """
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
        self._network_is_enabled = True
        self._networks: t.List[Network] = []

    def _stop_container(self) -> None:
        _stop_container(self._container)

    @contextlib.contextmanager
    def stopped_container(self
                          ) -> t.Generator['AutoTestContainer', None, None]:
        """Temporarily stop the container.

        The container will be stopped for the body of the ``with`` block.
        """
        self._stop_container()
        try:
            yield AutoTestContainer(self._name, self._config, self._container)
        finally:
            _start_container(self._container, always=True)

    def destroy_snapshots(self) -> None:
        """Destroy all snapshots of this container.
        """
        self._stop_container()
        with self._SNAPSHOT_LOCK, timed_code(
            'destroy_snapshots', snapshot_amount=len(self._snapshots)
        ):
            while self._snapshots:
                self._container.snapshot_destroy(self._snapshots.pop())

    def set_cgroup_item(self, key: str, value: str) -> None:
        """Set a cgroup option in the given container.

        :param key: The cgroup key to be set.
        :param value: The value to set.
        :raises AssertionError: When the value could not be set successfully.
        """
        with cg_logger.bound_to_logger(cgroup_key=key, cgroup_value=value):
            for _ in helpers.retry_loop(5):
                success = self._container.set_cgroup_item(key, value)
                if success:
                    return

    def _create_snapshot(self) -> None:
        with self._SNAPSHOT_LOCK:
            snap = self._container.snapshot()
            assert isinstance(snap, str)
            self._snapshots.append(snap)
            self._dirty = False

    @timed_function
    def disable_network(self) -> None:
        """Disable the network of this container.
        """
        if not self._network_is_enabled:
            return
        self._network_is_enabled = False
        self._stop_container()

        with self._NETWORK_LOCK:

            self._networks = []
            for network in self._container.network:
                net = (
                    network.type,
                    [(attr, getattr(network, attr)) for attr in dir(network)]
                )
                self._networks.append(Network(net))
            for network_idx in range(len(self._container.network)):
                assert self._container.network.remove(network_idx)

        _start_container(self._container, check_network=False)

    @timed_function
    def enable_network(self) -> None:
        """Enable the network of this container.
        """
        if self._network_is_enabled:
            return
        self._network_is_enabled = True
        self._stop_container()

        with self._NETWORK_LOCK:
            for typ, network in self._networks:
                assert self._container.network.add(typ)

                # -1 index doesn't work, as this isn't a true list
                last_index = len(self._container.network) - 1
                for key, value in network:
                    setattr(self._container.network[last_index], key, value)

        _start_container(self._container, check_network=True)

    @contextlib.contextmanager
    def as_snapshot(self, disable_network: bool = False
                    ) -> t.Generator['StartedContainer', None, None]:
        """Create a snapshot of the running container.

        .. warning::

          The state of the network of the container will be altered by doing
          this. To also restore the network use
          :meth:`.StartedContainer.enable_network` and
          :meth:`.StartedContainer.disable_network`.
        """
        # NOTE: This code never destroys snapshots, as this logic makes the
        # function way harder to follow. As we keep a dirty flag, only one
        # snapsnot will probably be created.

        _maybe_quit_running()

        if disable_network:
            self.disable_network()
        else:
            self.enable_network()

        try:

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
            # Creating the snapshot, so we might not have a snapshot
            if self._snapshots:
                self._stop_container()
                with self._SNAPSHOT_LOCK, timed_code('restore_snapshots'):
                    self._container.snapshot_restore(self._snapshots[-1])
                self._dirty = False
                _start_container(
                    self._container, check_network=not disable_network
                )

    @staticmethod
    def _read_fifo(
        files: t.Mapping[str, OutputCallback], stop: LockableValue[bool]
    ) -> None:
        fds = {}

        try:
            for fname, callback in files.items():
                # We use os primitives here to make sure we get a non blocking
                # file descriptor.
                f = os.open(fname, os.O_RDONLY | os.O_NONBLOCK)
                fds[f] = callback

            while fds and not stop.get():
                reads, _, _ = select.select(list(fds.keys()), [], [], 0.5)
                for f in reads:
                    # Read almost 1024, this is a low value as otherwise we
                    # might fill the limited output buffers with only one of
                    # the two file descriptors. (see
                    # ``_make_restricted_append`` for how the shared output
                    # buffers work).
                    data = os.read(f, 1024)
                    if data:
                        # We know that select returns a subset of its
                        # arguments, so ``f`` should always be in ``fds``.
                        fds[f](data)
                    else:
                        # This file descriptor is done, so remove it from our
                        # dictionary. Other fds might still be active so we
                        # don't return here.
                        os.close(f)
                        del fds[f]
        except:  # pylint: disable=bare-except
            # pragma: no cover
            logger.error(
                'Something went wrong when reading output', exc_info=True
            )
            raise
        finally:
            for f in fds:
                os.close(f)

    @staticmethod
    def _change_user(username: str) -> None:  # pragma: no cover
        # We cannot cover this as it is run in another process which will
        # execvp.
        pw_record = pwd.getpwnam(username)
        user_uid = pw_record.pw_uid
        user_gid = pw_record.pw_gid

        os.setgid(user_gid)
        os.setuid(user_uid)

    @staticmethod
    def _create_env(username: str) -> t.Dict:
        """Create the env for within a lxc subprocess call

        >>> import getpass
        >>> cur_user = getpass.getuser()
        >>> env = StartedContainer._create_env(cur_user)
        >>> env['USER'] == cur_user
        True
        >>> isinstance(env['USER'], str)
        True
        >>> isinstance(env['HOME'], str)
        True
        >>> isinstance(env['FIXTURES'], str)
        True
        >>> isinstance(env['STUDENT'], str)
        True
        """
        env = os.environ

        user = username
        home_dir = _get_home_dir(username)

        extra_path = (
            f'~/bin/:~/.pyenv/bin/:~/.local/bin:{home_dir}/.local/bin/'
            f':{home_dir}/bin/'
        )

        return {
            'PATH': f'{extra_path}:/usr/sbin/:/sbin/:{env["PATH"]}',
            'USER': user,
            'LOGUSER': user,
            'HOME': home_dir,
            'DEBIAN_FRONTEND': 'noninteractive',
            'TERM': 'dumb',
            'FIXTURES': f'{_get_home_dir(username)}/fixtures/',
            'STUDENT': f'{_get_home_dir(username)}/student/',
            'LANG': 'en_US.UTF-8',
            'LC_ALL': 'en_US.UTF-8',
        }

    def _run_command(
        self, cmd_user: t.Tuple[t.List[str], t.Optional[str]]
    ) -> int:
        cmd, user = cmd_user
        env = self._create_env(user or CODEGRADE_USER)

        if user:
            self._change_user(user)

        os.execvpe(cmd[0], cmd, env)

    def _run_shell(self, cmd_cwd_user: t.Tuple[str, str, str]) -> int:
        cmd, cwd, user = cmd_cwd_user
        env = self._create_env(user)
        home_dir = _get_home_dir(CODEGRADE_USER)
        env['PATH'] += f'{home_dir}/student/:{home_dir}/fixtures/'

        self._change_user(user)
        cmd_list = ['/bin/bash', '-c', cmd]
        os.chdir(cwd)

        os.execve(cmd_list[0], cmd_list, env)

    @staticmethod
    def _make_restricted_append(
        lst: t.List[bytes], size_left: LockableValue[int]
    ) -> t.Callable[[bytes], None]:
        r"""Make a restricted append function.

        The returned function will append its argument to ``lst`` while
        ``size_left`` is still higher than 0. It is safe to share ``size_left``
        between multiple append functions, the total size of all lists will not
        exceed ``size_left`` in this case.

        >>> from copy import deepcopy
        >>> max_size = LockableValue(10)
        >>> lst = []
        >>> append = StartedContainer._make_restricted_append(lst, max_size)
        >>> for i in range(100): append(str(i))
        >>> len(lst)
        11
        >>> lst[-1]
        b' <OUTPUT TRUNCATED>\n'
        >>> old_lst = deepcopy(lst)
        >>> append('something')
        >>> old_lst == lst
        True

        >>> max_size = LockableValue(10)
        >>> lst = []
        >>> append = StartedContainer._make_restricted_append(lst, max_size)
        >>> append('1234567890abcdefghi')
        >>> len(lst)
        2
        >>> lst[0]
        '1234567890'
        >>> lst2 = []
        >>> append2 = StartedContainer._make_restricted_append(lst2, max_size)
        >>> append2('bytes')
        >>> append2('bytes')
        >>> lst2
        [b' <OUTPUT TRUNCATED>\n']
        """
        outputed_truncated_emitted = False

        def emit_truncated() -> None:
            nonlocal outputed_truncated_emitted
            if not outputed_truncated_emitted:
                lst.append(b' <OUTPUT TRUNCATED>\n')
                outputed_truncated_emitted = True

        def fun(data: bytes) -> None:
            if outputed_truncated_emitted:
                return

            with size_left as inner:
                if inner.value < 0:
                    emit_truncated()
                    return
                elif len(data) > inner.value:
                    new_val = data[:inner.value]
                    if new_val:
                        lst.append(new_val)
                    emit_truncated()
                else:
                    lst.append(data)
                inner.value = inner.value - len(data)

        return fun

    def run_student_command(
        self,
        cmd: str,
        timeout: float,
        stdin: t.Union[None, bytes] = None,
        *,
        cwd: str = None,
    ) -> t.Tuple[int, str, str, float]:
        """Run a command provided by the student or teacher.

        The main difference between this function and
        :meth:`StartedContainer.run_command` is that the command here is a
        string and it will be executed by a shell.

        :param cmd: The command that should be executed.
        :param timeout: The maximum amount of time the command may take in
            seconds.
        :param stdin: The stdin that should be provided to the command.
        :param cwd: The location in which the command should be executed.
        :returns: A tuple of four items, which are respectively the exit code
            of the command, the produced stdout, the produced stderr and the
            time taken by the command.
        """
        stdout: t.List[bytes] = []
        stderr: t.List[bytes] = []

        user = CODEGRADE_USER
        if cwd is None:
            cwd = f'{_get_home_dir(user)}/student/'

        assert timeout > 0
        max_size = self._config['AUTO_TEST_OUTPUT_LIMIT']
        assert max_size > 0

        size_left = LockableValue(max_size)

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
                    stdout=self._make_restricted_append(stdout, size_left),
                    stderr=self._make_restricted_append(stderr, size_left),
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
                time_spend=e.time_spend,
            )

        stdout_str, stderr_str = get_stdout_and_stderr()
        return code, stdout_str, stderr_str, time_spend

    def run_command(
        self,
        cmd: t.List[str],
        stdout: t.Optional[OutputCallback] = None,
        stderr: t.Optional[OutputCallback] = None,
        stdin: t.Optional[bytes] = None,
        user: t.Optional[str] = None,
        check: bool = True,
        retry_amount: int = 1,
    ) -> int:
        """Run a command in this started container.

        :param cmd: The command argument list that should be run.
        :param stdout: A callback that will be called for when we recieve
            output on stdout. This might not contain full lines, or it might
            contain multiple lines.
        :param stdout: Same as ``stdout`` but for output to stderr.
        :param stdin: The stdin that should be provided to the container.
        :param user: The user that should run the command. If not provided the
            command will be executed by the root user.
        :param check: If ``true`` and exception will be raised when the exit
            code of the command is not 0.
        :param retry_amount: The amount of times the command will be retried
            when the exit code is not 0. This option has to be 1 if ``check``
            is ``False``.
        :returns: The exit code of the command.
        """
        ret: int = -1

        if retry_amount != 1:
            assert check

        for _ in helpers.retry_loop(
            retry_amount,
            sleep_time=0,
            make_exception=lambda: LXCProcessError(
                f'Command "{cmd}" crashed: {ret}',
            )
        ):
            ret = self._run(
                cmd=(cmd, user),
                callback=self._run_command,
                stdout=stdout,
                stderr=stderr,
                stdin=stdin,
                check=False,
                timeout=None
            )
            if not check or ret == 0:
                return ret

        raise RuntimeError

    def _run(
        self,
        cmd: T,
        callback: t.Callable[[T], int],
        stdout: t.Optional[OutputCallback],
        stderr: t.Optional[OutputCallback],
        stdin: t.Union[None, bytes],
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

            stop_reader_threads = LockableValue(False)
            reader_thread = threading.Thread(
                target=self._read_fifo,
                args=(
                    {
                        stdout_fifo: stdout or _make_log_function('stdout'),
                        stderr_fifo: stderr or _make_log_function('stderr')
                    }, stop_reader_threads
                )
            )
            reader_thread.start()

            # The order is really important here! We first need to close the
            # two fifo files before we join our threads. As otherwise the
            # threads will hang because they are still reading from these
            # files.
            with defer(reader_thread.join), open(
                stdout_fifo,
                'wb',
            ) as out, open(
                stderr_fifo,
                'wb',
            ) as err:
                assert timeout is None or timeout > 0
                _maybe_quit_running()

                pid = self._container.attach(
                    callback,
                    cmd,
                    stdout=out,
                    stderr=err,
                    stdin=stdin_file,
                )

                try:
                    res, left = _wait_for_pid(pid, timeout or sys.maxsize)
                except CommandTimeoutException:
                    logger.info(
                        'Exception occurred when waiting', exc_info=True
                    )
                    # Wait for 1 second to clear all remaining output.
                    left = 1
                    raise
                finally:
                    # Wait for at most a minute to clear all remaining output.
                    left = min(left, 60)
                    err.close()
                    out.close()
                    reader_thread.join(left)
                    stop_reader_threads.set(True)

            _maybe_quit_running()

            if check and res != 0:
                raise LXCProcessError(f'Command "{cmd}" crashed: {res}')

            return res


class AutoTestContainer:
    """This class represents a lxc container that will be used in an AutoTest.

    This container might be started, not started. To execute commands you
    should use the :class:`StartedContainer` class which can be obtained using
    the :meth:`AutoTestContainer.started_container` method.
    """

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
        """Get the name of this container.
        """
        return self._name

    def create(self) -> None:
        """Create a backing lxc container for this AutoTestContainer.
        """
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
        """Start a block wherein this container is started.
        """
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
        """Clone this container to a new container.

        :param new_name: The name of the new container, will be randomly
            generated if not provided.
        :returns: A clone of this container with the provided name.
        """
        _maybe_quit_running()

        new_name = new_name or _get_new_container_name()

        with self._lock, timed_code('clone_container'):
            cont = self._cont.clone(new_name)
            assert isinstance(cont, lxc.Container)
            return type(self)(new_name, self._config, cont)


class AutoTestRunner:
    """This class contains all functionality needed to run a single AutoTest.
    """

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
        self._reqs: t.Dict[t.Tuple[int, int], requests.Session] = {}

    @staticmethod
    def _make_req_key() -> t.Tuple[int, int]:
        """
        >>> import threading, multiprocessing
        >>> key = AutoTestRunner._make_req_key()
        >>> key == AutoTestRunner._make_req_key()
        True
        >>> def test_f(): print(AutoTestRunner._make_req_key() == key)
        >>> def test_ff(): assert AutoTestRunner._make_req_key() == key
        >>> t = threading.Thread(target=test_f)
        >>> t.start(); t.join()
        False
        >>> p = multiprocessing.Process(target=test_ff)
        >>> p.start(); p.join()
        >>> p.exitcode == 1
        True
        >>> key == AutoTestRunner._make_req_key()
        True
        """
        return os.getpid(), threading.get_ident()

    @property
    def req(self) -> requests.Session:
        """Get a request session unique for this thread and process.

        :returns: A requests session unique for this thread and process that
            has the correct headers for authentication.
        """
        key = self._make_req_key()

        if key not in self._reqs:
            req = requests.Session()
            req.auth = ('', '')
            req.headers.update(
                {
                    'CG-Internal-Api-Password': self._global_password,
                    'CG-Internal-Api-Runner-Password': self._local_password,
                }
            )
            self._reqs[key] = req
        return self._reqs[key]

    @property
    def _local_password(self) -> str:
        return self.instructions["runner_id"]

    @property
    def _wget_headers(self) -> t.List[str]:
        return [
            '--header',
            f'CG-Internal-Api-Password: {self._global_password}',
            '--header',
            f'CG-Internal-Api-Runner-Password: {self._local_password}',
        ]

    def download_file(
        self, cont: StartedContainer, url: str, dst: str
    ) -> None:
        """Download the given url to the given destination.

        :param cont: The container in which to download the files.
        :param url: The url from which to download the files.
        :param dst: The path in the container where to store the file.
        """
        dst = f'{_get_home_dir(CODEGRADE_USER)}/{dst}'
        cont.run_command(
            [
                'wget',
                *self._wget_headers,
                f'{self.base_url}/{url}',
                '-O',
                dst,
            ],
            user=CODEGRADE_USER,
            retry_amount=4,
        )
        cont.run_command(['chmod', '-R', '+x', dst], user=CODEGRADE_USER)
        logger.info('Downloaded file', dst=dst, url=url)

    def download_fixtures(self, cont: StartedContainer) -> None:
        """Download all the fixtures of this test.

        :param cont: The container in which the fixtures should be downloaded.
        """
        for name, fixture_id in self.fixtures:
            self.download_file(
                cont, f'fixtures/{fixture_id}', f'fixtures/{name}'
            )

        cont.run_command(
            ['ls', '-hl', f'{_get_home_dir(CODEGRADE_USER)}/fixtures/'],
            user=CODEGRADE_USER,
        )

    @timed_function
    def download_student_code(
        self, cont: StartedContainer, result_id: int
    ) -> None:
        """Download the code of the student.

        :param cont: The lxc container in which to download the code.
        :param result_id: The id of the code which should be downloaded.
        """
        url = f'results/{result_id}?type=submission_files'
        self.download_file(cont, url, 'student.zip')

        cont.run_command(
            [
                'unzip', f'{_get_home_dir(CODEGRADE_USER)}/student.zip', '-d',
                f'{_get_home_dir(CODEGRADE_USER)}/student/'
            ],
            user=CODEGRADE_USER
        )
        logger.info('Extracted student code')

        cont.run_command(
            ['chmod', '-R', '+x', f'{_get_home_dir(CODEGRADE_USER)}/student/'],
            user=CODEGRADE_USER
        )
        cont.run_command(
            ['rm', '-f', f'{_get_home_dir(CODEGRADE_USER)}/student.zip']
        )

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
                    log: t.Dict[str, object],
                    test_step: StepInstructions = test_step,
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

                with timed_code('run_suite_step'
                                ) as get_step_time, cg_logger.bound_to_logger(
                                    test_step=test_step
                                ):
                    try:
                        total_points += typ.execute_step(
                            snap, update_test_result, test_step, total_points
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
                        logger.info('Finished step', total_points=total_points)

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
                cont.run_command(['deluser', CODEGRADE_USER, 'sudo'])
                cont.run_command(
                    [
                        'sed', '-i', f's/^{CODEGRADE_USER}.*$//g',
                        '/etc/sudoers'
                    ]
                )
                assert cont.run_command(
                    ['grep', '-c', CODEGRADE_USER, '/etc/sudoers'],
                    check=False
                ) != 0, 'Sudo was not dropped!'

                total_points = 0.0

                for test_set in self.instructions['sets']:
                    for test_suite in test_set['suites']:
                        total_points += self._run_test_suite(
                            cont, result_id, test_suite
                        )
                        logger.info(
                            'Finished suite',
                            total_points=total_points,
                            test_suite=test_suite,
                        )
                    logger.info(
                        'Finished set',
                        total_points=total_points,
                        stop_points=test_set['stop_points'],
                        test_set=test_set,
                    )
                    if total_points < test_set['stop_points']:
                        break
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
        """Run the test for a single student.

        :param base_container_name: The name of the base lxc container.
        :param cpu_cores: The cpu cores which are available during testing.
        :param result_id: The id of the student to run.
        :returns: Nothing.
        """
        with _push_logging(self._push_log
                           ), cg_logger.bound_to_logger(result_id=result_id):
            self._run_student(base_container_name, cpu_cores, result_id)

    def _started_heartbeat(self) -> 'RepeatedTimer':
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
        """Run the test for all students using the given container as base.

        :param cont: The base container used for all students.
        :returns: Nothing.
        """
        run_result_url = f'{self.base_url}/runs/{self.instructions["run_id"]}'
        time_taken: t.Optional[float] = None
        push_log_timer = _push_logging(self._push_log).start()

        with self._started_heartbeat():
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
        self,
        cont: 'StartedContainer',
        cmd: str,
        url: str,
        cwd: str = None,
    ) -> None:
        if cmd:
            with timed_code(
                'run_setup_script', setup_cmd=cmd
            ) as get_time_spend:
                _, stdout, stderr, _ = cont.run_student_command(
                    cmd, 900, cwd=cwd
                )

            self.req.patch(
                url,
                json={
                    'setup_time_spend': get_time_spend(),
                    'setup_stdout': stdout,
                    'setup_stderr': stderr
                },
            )

    def _run_test(self, cont: StartedContainer) -> None:
        helpers.ensure_on_test_server()
        with timed_code('run_setup_commands'):
            cont.run_command(
                [
                    'adduser', '--shell', '/bin/bash', '--disabled-password',
                    '--gecos', '', CODEGRADE_USER
                ],
            )
            cont.run_command(
                ['mkdir', '-p', f'{_get_home_dir(CODEGRADE_USER)}/student/'],
                user=CODEGRADE_USER
            )
            cont.run_command(
                ['mkdir', '-p', f'{_get_home_dir(CODEGRADE_USER)}/fixtures/'],
                user=CODEGRADE_USER
            )

            cont.run_command(['usermod', '-aG', 'sudo', CODEGRADE_USER])

            cont.run_command(
                ['tee', '--append', '/etc/sudoers'],
                stdin=(f'\n{CODEGRADE_USER} ALL=(ALL) NOPASSWD: ALL\n'
                       ).encode('utf8')
            )
            cont.run_command(['grep', CODEGRADE_USER, '/etc/sudoers'])

        with timed_code('download_fixtures'):
            self.download_fixtures(cont)

        self._maybe_run_setup(
            cont,
            self.instructions['run_setup_script'],
            f'{self.base_url}/runs/{self.instructions["run_id"]}',
            cwd=f'{_get_home_dir(CODEGRADE_USER)}/fixtures/',
        )

        self.req.patch(
            f'{self.base_url}/runs/{self.instructions["run_id"]}',
            json={'state': models.AutoTestRunState.running.name},
        )

        with cont.stopped_container() as base_container, timed_code(
            'run_all_students'
        ), Manager() as manager, multiprocessing.Pool(
            # Over provision a bit so clones can be made quicker.
            _get_amount_cpus() + 4
        ) as pool:
            # Known issue from typeshed:
            # https://github.com/python/typeshed/issues/3018
            make_queue: t.Callable[[int], Queue
                                   ] = manager.Queue  # type: ignore
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
                        res.get(5)
                    except context.TimeoutError:
                        continue
                    else:
                        break
            except:
                _STOP_CONTAINERS.set()
                logger.error('AutoTest crashed', exc_info=True)
                raise
            else:
                logger.info('Done with containers, cleaning up')
                _STOP_CONTAINERS.set()
