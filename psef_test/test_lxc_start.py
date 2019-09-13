import sys
import threading

import pytest

from psef import helpers, auto_test


@pytest.mark.skip(reason='This only works locally when lxc works')
def test_run_command_a_lot(app, monkeypatch):
    monkeypatch.setattr(helpers, 'ensure_on_test_server', lambda: True)
    cont = auto_test._get_base_container(app.config)
    stop = threading.Event()

    def make_func(io):
        def func():
            while not stop.is_set():
                for _ in range(100):
                    io.write('Hello\n')

        return func

    t1 = threading.Thread(target=make_func(sys.stdout))
    t2 = threading.Thread(target=make_func(sys.stderr))

    t1.start()
    try:
        t2.start()
        try:
            with cont.started_container() as started:
                for i in range(25):
                    started.run_command([
                        'mkdir', '-p', f'/home/codegrade/student/{i}'
                    ], )
        finally:
            stop.set()
            t2.join()
    finally:
        stop.set()
        t1.join()
