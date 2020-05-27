"""This module contains the implementation of a signal.

A signal is an event that can happen somewhere in a app, which should trigger
actions somewhere else. Using signals has a few advantages:

1. Testing is way easier. We can simply test that a signal is emitted when we
    trigger the action and we can independently test the actions that should
    happen when the signal is triggered.
2. We keep logic in a single place. This is especially useful when we need to
    do a lot of things on a signal and there are many places were we might
    trigger them.
3. It is trivial to start doing some of the actions on a signal asynchronous:
    simply use :py:meth:`Signal.connect_celery` instead of
    :py:meth:`Signal.connect`.
4. Finally it is easier to work concurrently on features as reacting on a
    signal is done at the location of the new feature; no calls need to be
    added in existing code.

SPDX-License-Identifier: AGPL-3.0-only
"""
import typing as t
from inspect import getmodule

import structlog
from typing_extensions import Final, Literal

from cg_celery import Celery
from cg_flask_helpers import callback_after_this_request

logger = structlog.get_logger()

T = t.TypeVar('T')
Z = t.TypeVar('Z')
Y = t.TypeVar('Y')


class Signal(t.Generic[T]):
    """This class implements a signal.
    """
    __slots__ = (
        '__name',
        '__after_request_callbacks',
        '__immediate_callbacks',
        '__registered_functions',
        '__celery_todo',
    )

    def __init__(self, name: str) -> None:
        """Create a new signal with a given name.

        :param name: The name of the signal. This should be a unique name.
        """
        self.__name: Final = name
        self.__registered_functions: t.Set[str] = set()
        self.__after_request_callbacks: t.List[
            t.Tuple[str, t.Callable[[T], object]]] = []
        self.__immediate_callbacks: t.List[
            t.Tuple[str, t.Callable[[T], object]]] = []
        self.__celery_todo: t.List[t.Callable[[Celery], None]] = []

    def _check_function_not_registered(self, name: str) -> None:
        assert (
            name not in self.__registered_functions
        ), f'Function {name} is already registered.'

        self.__registered_functions.add(name)

    def send(self, value: T) -> None:
        """Send an event to this signal.

        :param value: The value you want to emit.
        :returns: Nothing.
        """
        logger.info('Sending signal', signal_name=self.__name)

        if self.__celery_todo:  # pragma: no cover
            raise AssertionError(
                'The Signal still has uninitialized celery listeners'
            )

        if self.__after_request_callbacks:

            def send_dispatch() -> None:
                for _, callback in self.__after_request_callbacks:
                    callback(value)

            callback_after_this_request(send_dispatch)

        for _, callback in self.__immediate_callbacks:
            callback(value)

    def __repr__(self) -> str:
        cls = self.__class__
        return '{}.{}({!r})'.format(getmodule(cls), cls.__name__, self.__name)

    def get_listners(self) -> t.Iterable[str]:
        """Get the names of all listeners on this signal.

        :yields: The names of the listeners (i.e. the functions that will
            react) of this signal.
        """
        yield from self.__registered_functions

    @staticmethod
    def _get_fullname(obj: object) -> str:
        module = getmodule(obj)
        name: str = getattr(
            obj, '__qualname__', getattr(obj, '__name__', '???')
        )
        return '{}.{}'.format(module.__name__ if module else '???', name)

    def finalize_celery(self, celery: Celery) -> None:
        """Finalize the celery listeners on this signal.

        This will register all these celery listeners on the given ``celery``
        instance.

        :param celery: The instance in which the celery tasks should be
            registered.
        """
        for fun in self.__celery_todo:
            fun(celery)
        self.__celery_todo.clear()

    def connect_celery(
        self,
        *,
        converter: t.Callable[[T], Z],
        pre_check: t.Callable[[T], bool] = lambda _: True,
        task_args: t.Mapping[str, t.Any] = None,
        prevent_recursion: bool = False,
    ) -> t.Callable[[t.Callable[[Z], Y]], t.Callable[[Z], Y]]:
        """Connect a method as celery task to this signal.

        :param converter: Convert the input data to something we can serialize
            for celery. This function should return something that can be
            serialized to JSON.
        :param pre_check: Function that will be called **before** the task is
            dispatched. This makes it possible to reduce the amount of celery
            tasks dispatched. Return ``False`` to prevent a celery task from
            being dispatched. Note that this function will called after the
            request, i.e. after the changes have been committed to the
            database.
        :param task_args: Extra arguments that will be passed to celery when
            creating the task. This makes it possible to setup retrying for
            example.
        :param prevent_recursion: Make sure that this method will never be
            called recursively. This means that if this signal is emitted
            within the task executing this method the signal is ignored for
            this method.
        """
        module = self.__class__.__module__

        def __inner(callback: t.Callable[[Z], Y]) -> t.Callable[[Z], Y]:
            fullname = self._get_fullname(callback)
            self._check_function_not_registered(fullname)
            task_name = (
                f'{module}.{self.__name}'
                f'.{self._get_fullname(callback)}.celery_task'
            )

            def __celery_setup(celery: Celery) -> None:
                @celery.task(name=task_name, **(task_args or {}))
                def __celery_task(arg: Z) -> Y:
                    return callback(arg)

                def __registered(arg: T) -> None:
                    if (
                        prevent_recursion and celery.current_task and
                        celery.current_task.name == task_name
                    ):
                        return
                    if pre_check(arg):
                        __celery_task.delay(converter(arg))

                self.__after_request_callbacks.append((fullname, __registered))

            self.__celery_todo.append(__celery_setup)
            return callback

        return __inner

    def disconnect(self, callback: t.Callable[[Y], Z]) -> None:
        """Disconnect the given callable from this signal.

        .. warning::

            This is, unlike in some other signal libraries, a slow operation at
            the moment. The current implementation is really meant for testing
            purposes only, for which is really useful.

        :param callback: The callback you want to disconnect from this signal.

        :returns: Nothing.
        """
        fullname = self._get_fullname(callback)
        assert fullname in self.__registered_functions

        self.__after_request_callbacks = [
            (name, cb) for (name, cb) in self.__after_request_callbacks
            if name != fullname
        ]
        self.__immediate_callbacks = [
            (name, cb) for (name, cb) in self.__immediate_callbacks
            if name != fullname
        ]
        self.__registered_functions.remove(fullname)

    def connect_immediate(
        self,
        callback: t.Callable[[T], Y],
    ) -> t.Callable[[T], Y]:
        """Connect a function to be called immediately after signal is
            dispatched.
        """
        return self.connect(
            'immediate',
            pre_check=lambda _: True,
            converter=lambda x: x,
        )(callback)

    def connect_after_request(
        self,
        callback: t.Callable[[T], Y],
    ) -> t.Callable[[T], Y]:
        """Connect a function to be called at the end of the request if the
            signal is dispatched.

        If the signal send multiple times the function will still be called
        multiple times.
        """
        return self.connect(
            'after_request',
            pre_check=lambda _: True,
            converter=lambda x: x,
        )(callback)

    def connect(
        self,
        when: Literal['immediate', 'after_request'],
        *,
        pre_check: t.Callable[[T], bool],
        converter: t.Callable[[T], Z],
    ) -> t.Callable[[t.Callable[[Z], Y]], t.Callable[[Z], Y]]:
        """Connect a signal.

        :param when: Should the callback be called immediately or after the
            request.
        :param pre_check: Should the signal be called at all. This check is
            called directly before the callback, even if ``when`` is
            ``after_request``.
        :param converter: Covert the input arguments to something else with
            which the callback will be called.
        """
        callbacks = (
            self.__immediate_callbacks
            if when == 'immediate' else self.__after_request_callbacks
        )

        def __wrapper(fun: t.Callable[[Z], Y]) -> t.Callable[[Z], Y]:
            fullname = self._get_fullname(fun)
            self._check_function_not_registered(fullname)

            def __callback(arg: T) -> None:
                if pre_check(arg):
                    fun(converter(arg))

            callbacks.append((fullname, __callback))

            return fun

        return __wrapper
