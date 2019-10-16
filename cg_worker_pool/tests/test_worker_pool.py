import time
import multiprocessing as mp

import pytest

from cg_worker_pool import (
    Work, WorkerPool, WorkerException, KillWorkerException
)


@pytest.fixture
def work_done():
    yield mp.Queue(1000)


@pytest.fixture
def continue_work():
    yield mp.Event()


class CustomExc(Exception):
    pass


def test_all_work_is_done_once(work_done):
    initial_work = [Work(i, i * 2) for i in range(500)]
    extra_work = [Work(i + 500, i * 2 + 1000) for i in range(50)]
    all_work = sorted(initial_work + extra_work)

    def worker_fun(opts):
        work = opts.get_work()
        if work:
            work_done.put(work)

    final_calls = 0

    def producer_fun(final_call):
        nonlocal final_calls

        if extra_work:
            res = extra_work[-2:]
            del extra_work[-2:]
            return res

        if final_call:
            final_calls += 1
        return []

    pool = WorkerPool(6, worker_fun, 0.1, 1, initial_work)

    pool.start(producer_fun)

    result = []
    while not work_done.empty():
        result.append(work_done.get())

    assert sorted(result) == all_work
    assert final_calls == 1


def test_newest_work_is_done(work_done, continue_work):
    initial_work = [
        Work(result_id=1, student_id=9),
        Work(result_id=23, student_id=9),
        Work(result_id=6, student_id=90),
    ]

    def worker_fun(opts):
        work = opts.get_work()
        if not work:
            return
        if work.student_id == 9:
            continue_work.wait()
            time.sleep(0.1)
        work_done.put(work)

    def producer(final):
        if continue_work.is_set():
            return []
        time.sleep(2)
        continue_work.set()
        return [initial_work[0], Work(result_id=7, student_id=90)]

    pool = WorkerPool(1, worker_fun, 6, 1, initial_work)
    pool.start(producer)

    assert work_done.get(False) == initial_work[1]
    assert work_done.get(False) == Work(result_id=7, student_id=90)
    assert work_done.empty()


def test_raises_exception():
    final_set = mp.Event()

    def worker_fun(opts):
        work = opts.get_work()
        if not work:
            return
        time.sleep(1)
        raise CustomExc(work.result_id)

    def producer(final):
        if final:  # pragma: no cover
            final_set.set()
        return []

    pool = WorkerPool(
        3, worker_fun, 2, 1, [
            Work(result_id=4, student_id=1),
            Work(result_id=5, student_id=2),
            Work(result_id=6, student_id=3),
        ]
    )
    with pytest.raises(WorkerException) as err:
        pool.start(producer)

    assert final_set.is_set() is False


def test_retry_work(work_done):
    def worker_fun(opts):
        work = opts.get_work()
        if work is None:
            return
        work_done.put(work)
        opts.retry_work(work)

    initial_work = [
        Work(result_id=4, student_id=1),
        Work(result_id=5, student_id=2),
        Work(result_id=6, student_id=3),
    ]
    pool = WorkerPool(3, worker_fun, 0, 1, initial_work)
    pool.start(lambda _: [])

    all_work = initial_work + initial_work + initial_work
    for _ in range(len(all_work)):
        all_work.remove(work_done.get(False))

    assert work_done.empty()
    assert not all_work


def test_killing_and_replacing_worker(work_done):
    def worker_fun(opts):
        work = opts.get_work()
        if work is None:
            return
        work_done.put(work)
        raise KillWorkerException

    initial_work = [
        Work(result_id=4, student_id=1),
        Work(result_id=5, student_id=2),
        Work(result_id=6, student_id=3),
    ]
    pool = WorkerPool(3, worker_fun, 0, 1, initial_work)
    pool.start(lambda _: [])

    all_work = initial_work
    for _ in range(len(all_work)):
        all_work.remove(work_done.get(False))

    assert work_done.empty()
    assert not all_work
