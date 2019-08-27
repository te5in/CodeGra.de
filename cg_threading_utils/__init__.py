"""This module contains utilities for working with threads.

SPDX-License-Identifier: AGPL-3.0-only
"""
import typing as t
import threading
from collections import deque


class FairLock:
    """This class contains a fair lock.

    A fair lock is a lock in which the order in which threads acquire it is
    equal to the order in which they called ``acquire``.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._locked = False
        self._wait_list: t.Deque[threading.Condition] = deque()

    def acquire(self) -> None:
        """Acquire the lock, this blocks until you have acquired it.

        .. note::

            Please use the context manager instead of manually acquiring it.
        """
        self._lock.acquire()

        while self._locked:
            cond = threading.Condition()
            self._wait_list.append(cond)
            with cond:
                self._lock.release()
                cond.wait()
                self._lock.acquire()

        assert not self._locked
        self._locked = True
        self._lock.release()

    def release(self) -> None:
        """Release the lock.
        """
        with self._lock:
            assert self._locked
            self._locked = False
            if self._wait_list:
                cond = self._wait_list.popleft()
                with cond:
                    cond.notify(1)

    def __enter__(self) -> None:
        self.acquire()

    def __exit__(
        self, exc_type: object, exc_value: object, traceback: object
    ) -> None:
        self.release()
