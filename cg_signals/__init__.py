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


class Dispatcher(t.Generic[T]):
    __slots__ = (
        '__name', '__after_request_callbacks', '__immediate_callbacks',
        '__registered_functions'
    )

    def __init__(self, name: str) -> None:
        self.__name = name
        self.__registered_functions: t.Set[str] = set()
        self.__after_request_callbacks: t.List[t.Callable[[T], object]] = []
        self.__immediate_callbacks: t.List[t.Callable[[T], object]] = []

    def _check_function_not_registered(self, name: str) -> None:
        assert (
            name not in self.__registered_functions
        ), f'Function {name} is already registered.'

        self.__registered_functions.add(name)

    def send(self, value: T) -> None:
        logger.info('Sending signal', signal_name=self.__name)

        if self.__after_request_callbacks:

            def send_dispatch() -> None:
                for callback in self.__after_request_callbacks:
                    callback(value)

            callback_after_this_request(send_dispatch)

        for callback in self.__immediate_callbacks:
            callback(value)

    def __repr__(self) -> str:
        cls = self.__class__
        return '{}.{}({!r})'.format(getmodule(cls), cls.__name__, self.__name)

    def get_listners(self) -> t.Iterable[str]:
        yield from self.__registered_functions

    @staticmethod
    def _get_fullname(obj: object) -> str:
        module = getmodule(obj)
        name: str = getattr(
            obj, '__qualname__', getattr(obj, '__name__', '???')
        )
        return '{}.{}'.format(module.__name__ if module else '???', name)

    def connect_celery(
        self,
        *,
        converter: t.Callable[[T], Z],
        celery: Celery,
        pre_check: t.Callable[[T], bool] = lambda _: True,
        task_args: t.Mapping[str, t.Any] = None,
    ) -> t.Callable[[t.Callable[[Z], Y]], t.Callable[[Z], Y]]:
        module = self.__class__.__module__

        def __inner(callback: t.Callable[[Z], Y]) -> t.Callable[[Z], Y]:
            assert celery is not None
            self._check_function_not_registered(self._get_fullname(callback))

            @celery.task(
                name=(
                    f'{module}.{self.__name}'
                    f'.{self._get_fullname(callback)}.celery_task'
                ),
                **(task_args or {})
            )
            def __celery_task(arg: Z) -> Y:
                return callback(arg)

            def __registered(arg: T) -> None:
                if pre_check(arg):
                    __celery_task.delay(converter(arg))

            self.__after_request_callbacks.append(__registered)

            return callback

        return __inner

    def connect_immediate(
        self,
        callback: t.Callable[[T], Y],
    ) -> t.Callable[[T], Y]:
        self._check_function_not_registered(self._get_fullname(callback))
        self.__immediate_callbacks.append(callback)
        return callback

    def connect_after_request(
        self,
        callback: t.Callable[[T], Y],
    ) -> t.Callable[[T], Y]:
        self._check_function_not_registered(self._get_fullname(callback))
        self.__after_request_callbacks.append(callback)
        return callback

    def connect(
        self, when: Literal['immediate', 'after_request'],
        converter: t.Callable[[T], Z], pre_check: t.Callable[[T], bool]
    ) -> t.Callable[[t.Callable[[Z], Y]], t.Callable[[Z], Y]]:
        callbacks = (
            self.__immediate_callbacks
            if when == 'immediate' else self.__after_request_callbacks
        )

        def __wrapper(fun: t.Callable[[Z], Y]) -> t.Callable[[Z], Y]:
            self._check_function_not_registered(self._get_fullname(fun))

            def __callback(arg: T) -> None:
                if pre_check(arg):
                    fun(converter(arg))

            callbacks.append(__callback)

            return fun

        return __wrapper