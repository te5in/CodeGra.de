import abc
import enum
import typing as t
import numbers
import datetime
import multiprocessing

import regex as re
import structlog
from sqlalchemy.types import JSON

import psef

from . import Base, db, _MyQuery
from . import auto_test as auto_test_models
from .. import auth, exceptions
from .mixins import IdMixin, TimestampMixin
from ..helpers import (
    JSONType, between, register, ensure_json_dict, ensure_on_test_server,
    get_from_map_transaction
)
from ..registry import auto_test_handlers
from ..exceptions import APICodes, APIException, StopRunningStepsException

logger = structlog.get_logger()

T = t.TypeVar('T', bound=t.Type['AutoTestStepBase'])

if t.TYPE_CHECKING and not getattr(t, 'SPHINX', False):  # pragma: no cover
    from .. import auto_test as auto_test_module

_all_auto_test_handlers = sorted([
    'io_test', 'run_program', 'custom_output', 'check_output', 'check_points'
])
_registered_test_handlers: t.Set[str] = set()


def _register(cls: T) -> T:
    name = cls.__mapper_args__['polymorphic_identity']

    assert name in _all_auto_test_handlers
    assert name not in _registered_test_handlers
    _registered_test_handlers.add(name)

    auto_test_handlers.register(name)(cls)
    return cls


def _ensure_program(program: str) -> None:
    if not program:
        raise APIException(
            'The program may to execute may not be empty',
            "The program to execute was empty, however it shouldn't be",
            APICodes.INVALID_PARAM, 400
        )


class AutoTestStepResultState(enum.Enum):
    not_started = enum.auto()
    running = enum.auto()
    passed = enum.auto()
    failed = enum.auto()
    timed_out = enum.auto()


class AutoTestStepBase(Base, TimestampMixin, IdMixin):
    __tablename__ = 'AutoTestStep'

    if t.TYPE_CHECKING:  # pragma: no cover
        query: t.ClassVar[_MyQuery['AutoTestStepBase']]
    id: int = db.Column('id', db.Integer, primary_key=True)

    order = db.Column('order', db.Integer, nullable=False)

    name: str = db.Column('name', db.Unicode, nullable=False)
    _weight: float = db.Column('weight', db.Float, nullable=False)

    hidden: bool = db.Column('hidden', db.Boolean, nullable=False)

    auto_test_suite_id: int = db.Column(
        'auto_test_suite_id',
        db.Integer,
        db.ForeignKey('AutoTestSuite.id'),
        nullable=False
    )

    suite: 'auto_test_models.AutoTestSuite' = db.relationship(
        'AutoTestSuite',
        foreign_keys=auto_test_suite_id,
        back_populates='steps',
        lazy='joined',
        innerjoin=True,
    )

    _test_type: str = db.Column(
        'test_type',
        db.Enum(*_all_auto_test_handlers, name='autoteststeptesttype'),
        nullable=False,
    )

    _data: 'psef.helpers.JSONType' = db.Column(
        'data', JSON, nullable=False, default={}
    )

    __mapper_args__ = {
        'polymorphic_on': _test_type,
        'polymorphic_identity': 'non_existing'
    }

    @property
    def data(self) -> 'psef.helpers.JSONType':
        return self._data

    @property
    def weight(self) -> float:
        return self._weight

    @weight.setter
    def weight(self, new_weight: float) -> None:
        self.validate_weight(new_weight)
        self._weight = new_weight

    def validate_weight(self, weight: float) -> None:
        if weight < 0:
            raise APIException(
                'The weight of a step cannot be negative',
                f'The weight is "{weight}" which is lower than 0',
                APICodes.INVALID_PARAM, 400
            )

    def update_data_from_json(
        self, json: t.Dict[str, 'psef.helpers.JSONType']
    ) -> None:
        self.validate_data(json)
        self._data = json

    def get_instructions(self) -> 'auto_test_module.StepInstructions':
        return {
            'id': self.id,
            'weight': self.weight,
            'test_type_name': self._test_type,
            'data': self.data,
        }

    def __to_json__(self) -> t.Mapping[str, object]:
        res = {
            'id': self.id,
            'name': self.name,
            'type': self._test_type,
            'weight': self.weight,
            'hidden': self.hidden
        }
        try:
            auth.ensure_can_view_autotest_step_details(self)
        except exceptions.PermissionException:
            pass
        else:
            res['data'] = self.data

        return res

    @abc.abstractmethod
    def validate_data(self, data: JSONType) -> None:
        raise NotImplementedError

    @classmethod
    def execute_step(
        cls,
        data: JSONType,
        container: 'auto_test_module.StartedContainer',
        update_test_result: 'auto_test_module.UpdateResultFunction',
        test_instructions: 'auto_test_module.StepInstructions',
        total_points: float,
    ) -> float:
        # Make sure we are not on a webserver
        ensure_on_test_server()

        update_test_result(AutoTestStepResultState.running, {})
        return cls._execute(
            data, container, update_test_result, test_instructions,
            total_points
        )

    @classmethod
    def _execute(
        cls,
        data: JSONType,
        container: 'auto_test_module.StartedContainer',
        update_test_result: 'auto_test_module.UpdateResultFunction',
        test_instructions: 'auto_test_module.StepInstructions',
        total_points: float,
    ) -> float:
        raise NotImplementedError

    def get_amount_achieved_points(
        self, result: 'AutoTestStepResult'
    ) -> float:
        if result.state == AutoTestStepResultState.passed:
            return result.step.weight
        return 0

    @staticmethod
    def remove_step_details(log: JSONType) -> JSONType:
        return t.cast(t.Dict[str, str], {})


@_register
class _IoTest(AutoTestStepBase):
    __mapper_args__ = {
        'polymorphic_identity': 'io_test',
    }
    data: t.Dict[str, object]

    def validate_data(self, data: JSONType) -> None:
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

            if weight < 0:
                errs.append((idx, 'The weight should not be lower than 0'))

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

        sum_weight = sum(i['weight'] for i in inputs)
        if sum_weight != self.weight:
            raise APIException(
                (
                    'The sum of the weight of the steps should be equal to the'
                    ' weight'
                ), (
                    f'The sum of the input weights is {sum_weight}, while the '
                    f'step weight is {self.weight}'
                ), APICodes.INVALID_PARAM, 400
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
        self, result: 'AutoTestStepResult'
    ) -> float:
        passed = AutoTestStepResultState.passed.name
        steps = t.cast(t.List, self.data['inputs'])
        step_results = t.cast(t.Dict[str, t.List], result.log).get('steps', [])
        it = zip(steps, step_results)

        return sum(s['weight'] if sr['state'] == passed else 0 for s, sr in it)

    @staticmethod
    def _execute(
        data: JSONType,
        cont: 'auto_test_module.StartedContainer',
        update_test_result: 'auto_test_module.UpdateResultFunction',
        _: 'auto_test_module.StepInstructions',
        __: float,
    ) -> float:
        def now() -> str:
            return datetime.datetime.utcnow().isoformat()

        assert isinstance(data, dict)
        inputs = t.cast(t.List[dict], data['inputs'])

        default_result = {
            'state': AutoTestStepResultState.not_started,
            'created_at': now(),
        }
        test_result: t.Dict[str, t.Any] = {
            'steps': [default_result for _ in inputs]
        }
        update_test_result(AutoTestStepResultState.running, test_result)

        prog = t.cast(str, data['program'])
        total_state = AutoTestStepResultState.failed
        total_weight = 0

        for idx, step in enumerate(inputs):
            test_result['steps'][idx].update(
                {
                    'state': AutoTestStepResultState.running,
                    'started_at': now(),
                }
            )
            update_test_result(AutoTestStepResultState.running, test_result)

            output = step['output'].rstrip('\n')

            options = t.cast(t.List[str], step['options'])
            time_spend: t.Optional[float]

            try:
                code, stdout, stderr, time_spend = cont.run_student_command(
                    f'{prog} {step["args"]}',
                    stdin=step['stdin'].encode('utf-8')
                )
            except psef.auto_test.CommandTimeoutException as e:
                code = -1
                stdout = e.stdout
                stderr = e.stderr
                time_spend = e.time_spend

            success = code == 0

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

            achieved_points = 0
            if success:
                total_state = AutoTestStepResultState.passed
                state = AutoTestStepResultState.passed
                total_weight += step['weight']
                achieved_points = step['weight']
            elif code < 0:
                state = AutoTestStepResultState.timed_out
            else:
                state = AutoTestStepResultState.failed

            test_result['steps'][idx].update(
                {
                    'stdout': stdout,
                    'stderr': stderr,
                    'state': state.name,
                    'exit_code': code,
                    'time_spend': time_spend,
                    'achieved_points': achieved_points,
                    'started_at': None,
                }
            )
            update_test_result(AutoTestStepResultState.running, test_result)

        update_test_result(total_state, test_result)
        return total_weight

    @staticmethod
    def remove_step_details(log: JSONType) -> JSONType:
        l = t.cast(t.Dict, log if isinstance(log, dict) else {})

        return {
            'steps':
                [
                    {
                        'achieved_points': step.get('achieved_points', None)
                    } for step in l.get('steps', [])
                ],
        }


@_register
class _RunProgram(AutoTestStepBase):
    __mapper_args__ = {
        'polymorphic_identity': 'run_program',
    }

    def validate_data(self, data: JSONType) -> None:
        with get_from_map_transaction(
            ensure_json_dict(data), ensure_empty=True
        ) as [get, _]:
            program = get('program', str)
        _ensure_program(program)

    @staticmethod
    def _execute(
        data: JSONType,
        container: 'auto_test_module.StartedContainer',
        update_test_result: 'auto_test_module.UpdateResultFunction',
        test_instructions: 'auto_test_module.StepInstructions',
        _: float,
    ) -> float:
        assert isinstance(data, dict)

        res = 0.0

        code, stdout, stderr, time_spend = container.run_student_command(
            t.cast(str, data['program'])
        )

        if code == 0:
            state = AutoTestStepResultState.passed
            res = test_instructions['weight']
        else:
            state = AutoTestStepResultState.failed

        update_test_result(
            state, {
                'stdout': stdout,
                'stderr': stderr,
                'exit_code': code,
                'time_spend': time_spend,
            }
        )

        return res


@_register
class _CustomOutput(AutoTestStepBase):
    __mapper_args__ = {
        'polymorphic_identity': 'custom_output',
    }

    def validate_data(self, data: JSONType) -> None:
        with get_from_map_transaction(
            ensure_json_dict(data), ensure_empty=True
        ) as [get, _]:
            program = get('program', str)
            regex = get('regex', str)

        _ensure_program(program)

        try:
            re.compile(regex)
        except re.error as e:
            raise APIException(
                f'Compiling the regex failed: {e.msg}',
                'Compiling was not successful', APICodes.INVALID_PARAM, 400
            )

    @staticmethod
    def _execute(
        data: JSONType,
        container: 'auto_test_module.StartedContainer',
        update_test_result: 'auto_test_module.UpdateResultFunction',
        test_instructions: 'auto_test_module.StepInstructions',
        _: float,
    ) -> float:
        assert isinstance(data, dict)
        regex = t.cast(str, data['regex'])

        code, stdout, stderr, time_spend = container.run_student_command(
            t.cast(str, data['program'])
        )
        if code == 0:
            state = AutoTestStepResultState.passed
            try:
                match = re.search(regex, stdout, flags=re.REVERSE, timeout=2)
            except TimeoutError:
                code = -3
                stderr += '\nSearching with the regex took too long'
            if match is None:
                code = -1
            else:
                try:
                    points = between(0, float(match.group(1)), 1)
                except ValueError:
                    code = -2

        if code != 0:
            state = AutoTestStepResultState.failed
            points = 0

        update_test_result(
            state, {
                'stdout': stdout,
                'stderr': stderr,
                'points': points,
                'exit_code': code,
                'time_spend': time_spend,
            }
        )

        return points * test_instructions['weight']

    def get_amount_achieved_points(_, result: 'AutoTestStepResult') -> float:
        if not isinstance(result.log, dict):
            return 0
        return t.cast(float, result.log.get('points', 0)) * result.step.weight


@_register
class _CheckPoints(AutoTestStepBase):
    __mapper_args__ = {
        'polymorphic_identity': 'check_points',
    }

    def validate_weight(self, weight: float) -> None:
        if weight != 0:
            raise APIException(
                'The weight of a "check_points" step can only be 0',
                f'The given weight of "{weight}" is invalid',
                APICodes.INVALID_PARAM, 400
            )

    def validate_data(self, data: JSONType) -> None:
        with get_from_map_transaction(
            ensure_json_dict(data), ensure_empty=True
        ) as [get, _]:
            get('min_points', numbers.Real)  # type: ignore

    @staticmethod
    def _execute(
        data: JSONType,
        _: 'auto_test_module.StartedContainer',
        update_test_result: 'auto_test_module.UpdateResultFunction',
        test_instructions: 'auto_test_module.StepInstructions',
        total_points: float,
    ) -> float:
        if total_points >= t.cast(dict,
                                  test_instructions['data'])['min_points']:
            update_test_result(AutoTestStepResultState.passed, {})
            return 0
        else:
            logger.warning(
                "Didn't score enough points", total_points=total_points
            )
            update_test_result(AutoTestStepResultState.failed, {})
            raise StopRunningStepsException('Not enough points')

    def get_amount_achieved_points(_, __: 'AutoTestStepResult') -> float:
        return 0


class AutoTestStepResult(Base, TimestampMixin, IdMixin):
    if t.TYPE_CHECKING:  # pragma: no cover
        query: t.ClassVar[_MyQuery['AutoTestStepResult']]

    auto_test_step_id: int = db.Column(
        'auto_test_step_id',
        db.Integer,
        db.ForeignKey('AutoTestStep.id'),
        nullable=False
    )

    step: AutoTestStepBase = db.relationship(
        'AutoTestStepBase',
        foreign_keys=auto_test_step_id,
        lazy='joined',
        innerjoin=True,
    )

    auto_test_result_id = db.Column(
        'auto_test_result_id',
        db.Integer,
        db.ForeignKey('AutoTestResult.id'),
    )

    result: 'auto_test_models.AutoTestResult' = db.relationship(
        'AutoTestResult',
        foreign_keys=auto_test_result_id,
        innerjoin=True,
        back_populates='step_results',
    )

    _state = db.Column(
        'state',
        db.Enum(AutoTestStepResultState),
        default=AutoTestStepResultState.not_started,
        nullable=False,
    )

    started_at: t.Optional[datetime.datetime] = db.Column(
        'started_at', db.DateTime, default=None, nullable=True
    )

    log: 'psef.helpers.JSONType' = db.Column(
        'log',
        JSON,
        nullable=True,
        default=None,
    )

    @property
    def state(self) -> AutoTestStepResultState:
        return self._state

    @state.setter
    def state(self, new_state: AutoTestStepResultState) -> None:
        if self._state == new_state:
            return

        self._state = new_state
        if new_state == AutoTestStepResultState.running:
            self.started_at = datetime.datetime.utcnow()
        else:
            self.started_at = None

    @property
    def achieved_points(self) -> float:
        return self.step.get_amount_achieved_points(self)

    def __to_json__(self) -> t.Mapping[str, object]:
        res = {
            'id': self.id,
            'auto_test_step': self.step,
            'state': self.state.name,
            'achieved_points': self.achieved_points,
            'log': self.log,
            'started_at': self.started_at and self.started_at.isoformat(),
        }
        if self.step.hidden:
            try:
                auth.ensure_can_view_autotest_step_details(self.step)
            except exceptions.PermissionException:
                res['log'] = self.step.remove_step_details(self.log)

        return res
