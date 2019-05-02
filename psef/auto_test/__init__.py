import re
import abc
import typing as t
import numbers
import dataclasses
import multiprocessing

import flask

from .. import current_tester
from ..helpers import (
    JSONType, register, ensure_json_dict, ensure_on_test_server,
    get_from_map_transaction
)
from ..exceptions import APICodes, APIException

auto_test_handlers: register.Register[str, t.
                                      Type['TestStep']] = register.Register()


def _ensure_program(program: str) -> None:
    if not program:
        raise APIException(
            'The program may to execute may not be empty',
            "The program to execute was empty, however it shouldn't be",
            APICodes.INVALID_PARAM, 400
        )

class TestStep(abc.ABC):
    def __init__(self, data: JSONType) -> None:
        self.data = data

    @classmethod
    @abc.abstractmethod
    def validate_data(cls, data: JSONType) -> None:
        raise NotImplementedError

    def execute_step(self) -> None:
        # Make sure we are not on webserver server
        ensure_on_test_server()
        self._execute()

    @abc.abstractmethod
    def _execute(self) -> None:
        raise NotImplementedError


@auto_test_handlers.register('io_test')
class IoTest(TestStep):
    @classmethod
    def validate_data(cls, data: JSONType) -> None:
        with get_from_map_transaction(
            ensure_json_dict(data), ensure_empty=True
        ) as [get, _]:
            inputs = get('inputs', list)
            program = get('program', str)

        _ensure_program(program)

        if not inputs:
            raise APIException(
                'You have to provide at least one input case',
                'No input cases where provided, however they are required',
                APICodes.INVALID_PARAM, 400
            )

        errs = []
        for idx, inp in enumerate(inputs):
            with get_from_map_transaction(ensure_json_dict(inp)) as [get, _]:
                name = get('name', str)
                weight: float = get('weight', numbers.Real)  # type: ignore
                get('args', str)
                get('stdin', str)
                get('output', str)
                get('options', list)

            if not name:
                errs.append((idx, 'The name may not be empty'))

            if weight <= 0:
                errs.append((idx, 'The weight should be higher than 0'))
        if errs:
            raise APIException(
                'Some input cases were not valid',
                'Some input cases were not valid',
                APICodes.INVALID_PARAM,
                400,
                invalid_cases=errs,
            )

    def _execute(self) -> None:
        print('hello')


@auto_test_handlers.register('run_program')
class RunProgram(TestStep):
    @classmethod
    def validate_data(cls, data: JSONType) -> None:
        with get_from_map_transaction(
            ensure_json_dict(data), ensure_empty=True
        ) as [get, _]:
            program = get('program', str)
        _ensure_program(program)


@auto_test_handlers.register('custom_output')
class CustomOutput(TestStep):
    @classmethod
    def validate_data(cls, data: JSONType) -> None:
        with get_from_map_transaction(
            ensure_json_dict(data), ensure_empty=True
        ) as [get, _]:
            program = get('program', str)
            regex = get('regex', str)

        _ensure_program(program)

        # We check the regex in another process to make sure that a very
        # complicated regex doesn't create a DOS attack. This should be
        # sufficient for now.
        with multiprocessing.Manager() as manager:
            # It does have this attribute:
            # https://docs.python.org/3/library/multiprocessing.html#sharing-state-between-processes
            d = manager.dict()  # type: ignore

            def worker(pattern: str, res: t.Dict[str, t.Any]) -> None:
                try:
                    re.compile(pattern)
                except re.error as e:
                    res['err'] = True
                    # It does have this attribute:
                    # https://docs.python.org/3/library/re.html#re.error
                    res['msg'] = e.msg  # type: ignore
                else:
                    res['err'] = False

            proc = multiprocessing.Process(target=worker, args=(regex, d))
            proc.start()
            proc.join(1)

            if proc.is_alive():
                proc.terminate()
                proc.join()
                raise APIException(
                    'Compiling the regex took too long, try a simpler regex',
                    'Compiling the regex took longer than 1 second',
                    APICodes.INVALID_PARAM, 400
                )
            elif d['err']:
                raise APIException(
                    'Compiling the regex failed: {}'.format(d['msg']),
                    'Compiling was not successful',
                    APICodes.INVALID_PARAM, 400
                )


@auto_test_handlers.register('check_points')
class CheckPoints(TestStep):
    @classmethod
    def validate_data(cls, data: JSONType) -> None:
        pass
