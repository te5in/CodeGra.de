import time
import threading

from cg_threading_utils import FairLock

# The `time.sleep(0)` calls are here to let the thread yield the GIL.


def test_acquire():
    lock = FairLock()
    res = 0
    t_amount = 1000
    threads = []

    def fun():
        nonlocal res
        time.sleep(0)
        with lock:
            res += 1
            time.sleep(0)

    threads = [threading.Thread(target=fun) for _ in range(t_amount)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert res == t_amount


def get_diff(lock):
    res = []
    t_amount = 1000
    threads = []

    def fun(i):
        time.sleep(0)
        with lock:
            res.append(i)
            time.sleep(0)

    threads = [
        threading.Thread(target=fun, args=(i, )) for i in range(t_amount)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(res) == t_amount
    res = sum(
        abs(r1 - r2) for r1, r2 in zip(res, range(t_amount))
        if abs(r1 - r2) > 3
    )
    print(lock, res)
    return res


def test_fairness():
    success = []
    for _ in range(150):
        ours = get_diff(FairLock())
        theirs = get_diff(threading.Lock())
        success.append(ours <= theirs)

    assert sum(success) > (len(success) / 2)
