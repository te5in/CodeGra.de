import os
import sys
import multiprocessing
import multiprocessing.managers
from copy import deepcopy

import pytest
import pytest_cov.embed


@pytest.fixture
def lxc_stub(stub_function_class):
    class LXC:
        def __init__(self, name):
            self._name = name
            self.__destroyed = False

            def mk_fn(attr):
                def inner(*args, **kwargs):
                    getattr(self, attr)()
                    return attr

                return inner

            check = mk_fn('_check')

            self.running = False
            self.create = stub_function_class(check)
            self.destroy_snapshots = stub_function_class(check)
            self.destroy = stub_function_class(self.__destroy)
            self.snapshot = stub_function_class(check)
            self.snapshot_restore = stub_function_class(check)
            self.snapshot_destroy = stub_function_class(check)

            def set_running(val):
                self.running = True
                return True

            self.start = stub_function_class(lambda: set_running(True))
            self.wait = stub_function_class(lambda: True)
            self.get_ips = stub_function_class(lambda: True)
            self.stop = stub_function_class(lambda: set_running(False))

            class StubNetwork:
                type = 'nw-type-1'

                def __dir__(self):
                    return ['type']

            class StubNetworkList(list):
                def add(self, val):
                    assert val == StubNetwork.type
                    self.append(StubNetwork())
                    return True

            StubNetworkList.remove = StubNetworkList.pop

            self.network = StubNetworkList([StubNetwork()])

        def clone(self, new_name):
            return type(self)(new_name)

        def _check(self):
            assert not self.__destroyed

        def __destroy(self):
            self._check()
            self.__destroyed = True

        def set_cgroup_item(self, key, value):
            assert isinstance(value, str)
            assert key in {
                'memory.limit_in_bytes',
                'cpuset.cpus',
                'memory.memsw.limit_in_bytes',
            }
            return True

        def attach_wait(self, callback, cmd):
            with open('/dev/null', 'wb') as w, open('/dev/null', 'rb') as r:
                pid = self.attach(callback, cmd, r, r, w)
                _, res = os.waitpid(pid, 0)
                assert os.WIFEXITED(res)
                return os.WEXITSTATUS(res)

        def attach(self, callback, cmd, stdout, stderr, stdin):
            assert self.running
            pid = os.fork()

            if pid == 0:
                if pytest_cov.embed._active_cov is None:
                    pytest_cov.embed.init()
                os.dup2(stdin.fileno(), 0)
                os.dup2(stdout.fileno(), 1)
                os.dup2(stderr.fileno(), 2)
                ret = callback(cmd)
                pytest_cov.embed.cleanup()
                assert isinstance(ret, int)
                os._exit(ret)
                assert False

            return pid

    yield LXC
