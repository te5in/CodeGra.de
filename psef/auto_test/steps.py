import re
import abc
import typing as t
import numbers
import dataclasses
import multiprocessing

import flask
import structlog

import psef

from .. import models, current_tester
from ..helpers import (
    JSONType, between, register, ensure_json_dict, ensure_on_test_server,
    get_from_map_transaction
)
from ..exceptions import APICodes, APIException

logger = structlog.get_logger()

auto_test_handlers: register.Register[str, t.
                                      Type['TestStep']] = register.Register()

if t.TYPE_CHECKING and not getattr(t, 'SPHINX', False):  # pragma: no cover
    from . import StartedContainer, StepInstructions


def _ensure_program(program: str) -> None:
    if not program:
        raise APIException(
            'The program may to execute may not be empty',
            "The program to execute was empty, however it shouldn't be",
            APICodes.INVALID_PARAM, 400
        )


UpdateResultFunction = t.Callable[
    ['models.AutoTestStepResultState', t.Dict[str, object]], None]


class StopRunningStepsException(Exception):
    pass


class TestStep(abc.ABC):
    def __init__(self, data: JSONType) -> None:
        self.data = data

    @classmethod
    @abc.abstractmethod
    def validate_data(cls, data: JSONType) -> None:
        raise NotImplementedError

    def execute_step(
        self,
        container: 'StartedContainer',
        update_test_result: UpdateResultFunction,
        test_instructions: 'StepInstructions',
        total_points: float,
    ) -> float:
        # Make sure we are not on a webserver
        ensure_on_test_server()

        update_test_result(models.AutoTestStepResultState.running, {})
        return self._execute(
            container, update_test_result, test_instructions, total_points
        )

    @abc.abstractmethod
    def _execute(
        self,
        container: 'StartedContainer',
        update_test_result: UpdateResultFunction,
        test_instructions: 'StepInstructions',
        total_points: float,
    ) -> float:
        raise NotImplementedError

    def get_amount_achieved_points(
        self, result: 'models.AutoTestStepResult'
    ) -> float:
        if result.state == models.AutoTestStepResultState.passed:
            return result.step.weight
        return 0


@auto_test_handlers.register('io_test')
class IoTest(TestStep):
    data: t.Dict[str, object]

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
                options = get('options', list)

            if not name:
                errs.append((idx, 'The name may not be empty'))

            if weight <= 0:
                errs.append((idx, 'The weight should be higher than 0'))

            extra_items = set(options) - {
                'case', 'trailing_whitespace', 'substring', 'regex'
            }
            if extra_items:
                errs.append(
                    (idx, 'Unknown items found: "{", ".join(extra_items)}"')
                )
            if len(options) != len(set(options)):
                errs.append((idx, 'Duplicate options are not allowed'))
            if 'regex' in options and len(options) > 1:
                errs.append(
                    (
                        idx, (
                            'The "regex" option cannot be used in combination'
                            ' with other options.'
                        )
                    )
                )
        if errs:
            raise APIException(
                'Some input cases were not valid',
                'Some input cases were not valid',
                APICodes.INVALID_PARAM,
                400,
                invalid_cases=errs,
            )

    def get_amount_achieved_points(
        self, result: 'models.AutoTestStepResult'
    ) -> float:
        passed = models.AutoTestStepResultState.passed.name
        steps = t.cast(t.List, self.data['inputs'])
        step_results = t.cast(t.Dict[str, t.List], result.log).get('steps', [])
        it = zip(steps, step_results)

        return sum(s['weight'] if sr['state'] == passed else 0 for s, sr in it)

    def _execute(
        self,
        container: 'StartedContainer',
        update_test_result: UpdateResultFunction,
        _: 'StepInstructions',
        __: float,
    ) -> float:
        test_result: t.Dict[str, t.Any] = {'steps': []}

        assert isinstance(self.data, dict)
        prog = t.cast(str, self.data['program'])
        total_state = models.AutoTestStepResultState.failed
        total_weight = 0

        for step in t.cast(t.List[dict], self.data['inputs']):
            output = step['output'].rstrip('\n')

            options = t.cast(t.List[str], step['options'])
            code, stdout, stderr = container.run_student_command(
                f'{prog} {step["args"]}', stdin=step['stdin'].encode('utf-8')
            )
            if code == 0:
                to_test = stdout.rstrip('\n')

                if 'trailing_whitespace' in options:
                    to_test = '\n'.join(
                        line.rstrip() for line in to_test.splitlines()
                    )
                    output = '\n'.join(
                        line.rstrip() for line in output.splitlines()
                    )

                if 'case' in options:
                    to_test = to_test.lower()
                    output = output.lower()

                if 'substring' in options:
                    success = output in to_test
                else:
                    success = output == to_test
            else:
                success = False
                if code < 0:
                    state = models.AutoTestStepResultState.timed_out
                else:
                    state = models.AutoTestStepResultState.failed

            if success:
                total_state = models.AutoTestStepResultState.passed
                state = models.AutoTestStepResultState.passed
                total_weight += step['weight']
            else:
                state = models.AutoTestStepResultState.failed

            test_result['steps'].append(
                {
                    'stdout': stdout,
                    'stderr': stderr,
                    'state': state.name,
                    'exit_code': code,
                }
            )
            update_test_result(
                models.AutoTestStepResultState.running, test_result
            )

        update_test_result(total_state, test_result)
        return total_weight


@auto_test_handlers.register('run_program')
class RunProgram(TestStep):
    @classmethod
    def validate_data(cls, data: JSONType) -> None:
        with get_from_map_transaction(
            ensure_json_dict(data), ensure_empty=True
        ) as [get, _]:
            program = get('program', str)
        _ensure_program(program)

    def _execute(
        self,
        container: 'StartedContainer',
        update_test_result: UpdateResultFunction,
        test_instructions: 'StepInstructions',
        _: float,
    ) -> float:
        assert isinstance(self.data, dict)

        res = 0.0

        code, stdout, stderr = container.run_student_command(
            t.cast(str, self.data['program'])
        )

        if code == 0:
            state = models.AutoTestStepResultState.passed
            res = test_instructions['weight']
        else:
            state = models.AutoTestStepResultState.failed

        update_test_result(
            state, {
                'stdout': stdout,
                'stderr': stderr,
                'exit_code': code,
            }
        )

        return res


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
                    'Compiling was not successful', APICodes.INVALID_PARAM, 400
                )

    def _execute(
        self,
        container: 'StartedContainer',
        update_test_result: UpdateResultFunction,
        test_instructions: 'StepInstructions',
        _: float,
    ) -> float:
        assert isinstance(self.data, dict)
        regex = t.cast(str, self.data['regex'])
        res = 0

        code, stdout, stderr = container.run_student_command(
            t.cast(str, self.data['program'])
        )
        if code == 0:
            state = models.AutoTestStepResultState.passed
            match = re.match(regex, stdout)
            if match is None:
                code = -1
            else:
                try:
                    points = between(0, float(match.group(1)), 1)
                except ValueError:
                    code = -2

        if code != 0:
            state = models.AutoTestStepResultState.failed
            points = 0

        update_test_result(
            state, {
                'stdout': stdout,
                'stderr': stderr,
                'points': points,
                'exit_code': code,
            }
        )

        return points * test_instructions['weight']

    def get_amount_achieved_points(
        _, result: 'models.AutoTestStepResult'
    ) -> float:
        if not isinstance(result.log, dict):
            return 0
        return t.cast(float, result.log['points']) * result.step.weight


@auto_test_handlers.register('check_points')
class CheckPoints(TestStep):
    @classmethod
    def validate_data(cls, data: JSONType) -> None:
        with get_from_map_transaction(
            ensure_json_dict(data), ensure_empty=True
        ) as [get, _]:
            get('min_points', float)

    def _execute(
        self,
        _: 'StartedContainer',
        update_test_result: UpdateResultFunction,
        test_instructions: 'StepInstructions',
        total_points: float,
    ) -> float:
        if total_points >= t.cast(dict,
                                  test_instructions['data'])['min_points']:
            update_test_result(models.AutoTestStepResultState.passed, {})
            return 0
        else:
            logger.warning(
                "Didn't score enough points", total_points=total_points
            )
            update_test_result(models.AutoTestStepResultState.failed, {})
            raise StopRunningStepsException('Not enough points')

    def get_amount_achieved_points(
        _, __: 'models.AutoTestStepResult'
    ) -> float:
        return 0
