"""This module defines all models needed for a step of an AutoTest.

This module also contains the code needed to execute each step.

SPDX-License-Identifier: AGPL-3.0-only
"""
import abc
import copy
import enum
import typing as t
import numbers
import datetime

import regex as re
import structlog
from sqlalchemy.types import JSON

import psef
import cg_logger
from cg_sqlalchemy_helpers.mixins import IdMixin, TimestampMixin

from . import Base, db, _MyQuery
from .. import auth, helpers, exceptions
from ..helpers import (
    JSONType, between, ensure_json_dict, get_from_map_transaction
)
from ..registry import auto_test_handlers
from ..exceptions import (
    APICodes, APIWarnings, APIException, StopRunningStepsException
)

logger = structlog.get_logger()

T = t.TypeVar('T', bound=t.Type['AutoTestStepBase'])

if t.TYPE_CHECKING and not getattr(t, 'SPHINX', False):  # pragma: no cover
    # pylint: disable=unused-import
    from . import auto_test as auto_test_models
    from .. import auto_test as auto_test_module

_ALL_AUTO_TEST_HANDLERS = sorted(
    ['io_test', 'run_program', 'custom_output', 'check_points']
)
_registered_test_handlers: t.Set[str] = set()


def _register(cls: T) -> T:
    name = cls.__mapper_args__['polymorphic_identity']

    assert name in _ALL_AUTO_TEST_HANDLERS
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
    """This enum represents the states the result of a step can be in.

    A single step result will probably be in multiple states during its
    existence.
    """
    not_started = enum.auto()
    running = enum.auto()
    passed = enum.auto()
    failed = enum.auto()
    timed_out = enum.auto()


class AutoTestStepBase(Base, TimestampMixin, IdMixin):
    """The base class that every step inherits.

    This class provides represents a single step, and contains the code needed
    to execute it.
    """
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
        db.Enum(*_ALL_AUTO_TEST_HANDLERS, name='autoteststeptesttype'),
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
        """Get the data for this step.
        """
        return self._data

    @property
    def weight(self) -> float:
        """Get the weight for this step.
        """
        return self._weight

    @weight.setter
    def weight(self, new_weight: float) -> None:
        self.validate_weight(new_weight)
        self._weight = new_weight

    @staticmethod
    def validate_weight(weight: float) -> None:
        """
        >>> AutoTestStepBase.validate_weight(0) is None
        True
        >>> AutoTestStepBase.validate_weight(-1)
        Traceback (most recent call last):
        ...
        psef.exceptions.APIException
        """
        if weight < 0:
            raise APIException(
                'The weight of a step cannot be negative',
                f'The weight is "{weight}" which is lower than 0',
                APICodes.INVALID_PARAM, 400
            )

    def update_data_from_json(
        self, json: t.Dict[str, 'psef.helpers.JSONType']
    ) -> None:
        """
        >>> t = AutoTestStepBase()
        >>> t.validate_data = lambda _: print('CALLED!')
        >>> d = object()
        >>> t.update_data_from_json(d)
        CALLED!
        >>> t.data is d
        True
        """
        self.validate_data(json)
        self._data = json

    @property
    def command_time_limit(self) -> float:
        """Get the command time limit for this step.
        """
        return (
            self.suite.command_time_limit or
            psef.app.config['AUTO_TEST_MAX_TIME_COMMAND']
        )

    def get_instructions(self) -> 'auto_test_module.StepInstructions':
        return {
            'id': self.id,
            'weight': self.weight,
            'test_type_name': self._test_type,
            'data': self.data,
            'command_time_limit': self.command_time_limit,
        }

    def __to_json__(self) -> t.Mapping[str, object]:
        res = {
            'id': self.id,
            'name': self.name,
            'type': self._test_type,
            'weight': self.weight,
            'hidden': self.hidden,
            'data': {},
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
        """Validate that the given data is valid data for this step.
        """
        raise NotImplementedError

    @classmethod
    def execute_step(
        cls,
        container: 'auto_test_module.StartedContainer',
        update_test_result: 'auto_test_module.UpdateResultFunction',
        test_instructions: 'auto_test_module.StepInstructions',
        total_points: float,
    ) -> float:
        """Execute this step.

        .. danger::

            You should only do this on a test server. This function also checks
            this, but it is important to be sure from the calling code too as
            this function will execute user provided (untrusted) code.

        :param container: The container to execute the code in.
        :parm update_test_result: A function that can be used to update the
            result of the step.
        :param test_instructions: The test instructions for this step.
        :param total_points: The total amount of points achieved in the current
            test suite (category).
        :returns: The amount of points achieved in this step.
        """
        # Make sure we are not on a webserver
        helpers.ensure_on_test_server()

        update_test_result(AutoTestStepResultState.running, {})
        return cls._execute(
            container, update_test_result, test_instructions, total_points
        )

    @classmethod
    def _execute(
        cls,
        container: 'auto_test_module.StartedContainer',
        update_test_result: 'auto_test_module.UpdateResultFunction',
        test_instructions: 'auto_test_module.StepInstructions',
        total_points: float,
    ) -> float:
        raise NotImplementedError

    def get_amount_achieved_points(  # pylint: disable=no-self-use
        self, result: 'AutoTestStepResult'
    ) -> float:
        """Get the amount of achieved points in this step using the given
        result.
        """
        if result.state == AutoTestStepResultState.passed:
            return result.step.weight
        return 0

    @staticmethod
    def remove_step_details(_: JSONType) -> JSONType:
        """Remove the step details from the result log.

        >>> AutoTestStepBase.remove_step_details(object())
        {}
        >>> AutoTestStepBase.remove_step_details({'secret': 'key'})
        {}
        """
        return t.cast(t.Dict[str, str], {})


@_register
class _IoTest(AutoTestStepBase):
    __mapper_args__ = {
        'polymorphic_identity': 'io_test',
    }
    data: t.Dict[str, object]

    _ALL_OPTIONS = {
        'case', 'trailing_whitespace', 'substring', 'regex', 'all_whitespace'
    }

    _REQUIRES_MAP = {
        'all_whitespace': 'trailing_whitespace',
        'regex': 'substring',
    }

    _NOT_ALLOWED_MAP = {
        'all_whitespace': 'regex',
    }

    @staticmethod
    def _remove_whitespace(string: str) -> str:
        return "".join(string.split())

    @classmethod
    def _validate_single_input(cls, inp: JSONType) -> t.List[str]:
        errs = []
        with get_from_map_transaction(ensure_json_dict(inp)) as [get, _]:
            name = get('name', str)
            weight: float = get('weight', numbers.Real)  # type: ignore
            get('args', str)
            get('stdin', str)
            get('output', str)
            options = get('options', list)

        if not name:
            errs.append('The name may not be empty')

        if weight < 0:
            errs.append('The weight should not be lower than 0')

        extra_items = set(options) - cls._ALL_OPTIONS
        if extra_items:
            errs.append(f'Unknown items found: "{", ".join(extra_items)}"')
        if len(options) != len(set(options)):
            errs.append('Duplicate options are not allowed')

        for item, required in cls._REQUIRES_MAP.items():
            if item in options and required not in options:
                errs.append(f'The "{item}" option implies "{required}"')

        for item, not_allowed in cls._NOT_ALLOWED_MAP.items():
            if item in options and not_allowed in options:
                errs.append(
                    f'The "{item}" option cannot be combined with the '
                    f'"{not_allowed}" option'
                )

        return errs

    def validate_data(self, data: JSONType) -> None:
        """Validate if the given data is valid for a io test.
        """
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

        errs: t.List[t.Tuple[int, str]] = []
        for idx, inp in enumerate(inputs):
            errs.extend((idx, err) for err in self._validate_single_input(inp))

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
        iterator = zip(steps, step_results)

        return sum(
            s['weight'] if sr['state'] == passed else 0 for s, sr in iterator
        )

    @classmethod
    def match_output(
        cls, stdout: str, expected_output: str, step_options: t.Iterable[str]
    ) -> t.Tuple[bool, t.Optional[int]]:
        """Do the output matching of an IoTest.

        :param stdout: The stdout of the program, so the thing we got.
        :param expected_output: The expected output as provided by the teacher,
            this might be a regex.
        :param step_options: A list of options as given by the students. Valid
            options are 'regex', 'trailing_whitespace', 'case' and 'substring'.
        """
        regex_flags = 0
        to_test = stdout.rstrip('\n')
        step_options = set(step_options)

        if 'all_whitespace' in step_options:
            to_test = cls._remove_whitespace(to_test)
            expected_output = cls._remove_whitespace(expected_output)
        elif 'trailing_whitespace' in step_options:
            to_test = '\n'.join(line.rstrip() for line in to_test.splitlines())
            expected_output = '\n'.join(
                line.rstrip() for line in expected_output.splitlines()
            )

        if 'case' in step_options:
            regex_flags |= re.IGNORECASE
            if 'regex' not in step_options:
                to_test = to_test.lower()
                expected_output = expected_output.lower()

        logger.info(
            'Comparing output and expected output',
            to_test=to_test,
            expected_output=expected_output,
            step_options=step_options,
        )
        if 'regex' in step_options:
            with cg_logger.bound_to_logger(
                output=expected_output,
                to_test=to_test,
                flags=regex_flags,
            ):
                try:
                    match = re.search(
                        expected_output,
                        to_test,
                        flags=regex_flags,
                        timeout=2,
                    )
                except TimeoutError:
                    logger.warning('Regex match timed out', exc_info=True)
                    return False, -2
                logger.info('Done with regex search', match=match)
            return bool(match), None
        elif 'substring' in step_options:
            return expected_output in to_test, None
        else:
            return expected_output == to_test, None

    @classmethod
    def _execute(
        cls,
        container: 'auto_test_module.StartedContainer',
        update_test_result: 'auto_test_module.UpdateResultFunction',
        test_instructions: 'auto_test_module.StepInstructions',
        total_points: float,
    ) -> float:
        def now() -> str:
            return datetime.datetime.utcnow().isoformat()

        data = test_instructions['data']
        assert isinstance(data, dict)
        inputs = t.cast(t.List[dict], data['inputs'])

        default_result = {
            'state': AutoTestStepResultState.not_started.name,
            'created_at': now(),
        }
        test_result: t.Dict[str, t.Any] = {
            'steps': [copy.deepcopy(default_result) for _ in inputs]
        }
        update_test_result(AutoTestStepResultState.running, test_result)

        prog = t.cast(str, data['program'])
        time_limit = test_instructions['command_time_limit']
        total_state = AutoTestStepResultState.failed
        total_weight = 0

        for idx, step in enumerate(inputs):
            test_result['steps'][idx].update(
                {
                    'state': AutoTestStepResultState.running.name,
                    'started_at': now(),
                }
            )
            update_test_result(AutoTestStepResultState.running, test_result)

            try:
                res = container.run_student_command(
                    f'{prog} {step["args"]}',
                    time_limit,
                    stdin=step['stdin'].encode('utf-8')
                )
                code, stdout, stderr, time_spend = res
            except psef.auto_test.CommandTimeoutException as e:
                code = -1
                stderr = e.stderr
                stdout = e.stdout
                time_spend = e.time_spend

            if code == 0:
                step_options = t.cast(t.List[str], step['options'])
                expected_output = step['output'].rstrip('\n')

                with cg_logger.bound_to_logger(step=step):
                    success, new_code = cls.match_output(
                        stdout, expected_output, step_options
                    )
                code = code if new_code is None else new_code
            else:
                success = False

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
        """Remove the step details for a IoTest result.

        >>> _IoTest.remove_step_details(None)
        {'steps': []}
        >>> step = {'achieved_points': 5, 'other': 'key'}
        >>> res = _IoTest.remove_step_details({'steps': [step]})
        >>> res
        {'steps': [{'achieved_points': 5}]}
        """
        log_dict = t.cast(t.Dict, log if isinstance(log, dict) else {})
        steps = log_dict.get('steps', [])
        steps = [{'achieved_points': s.get('achieved_points')} for s in steps]
        return {'steps': steps}


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
        container: 'auto_test_module.StartedContainer',
        update_test_result: 'auto_test_module.UpdateResultFunction',
        test_instructions: 'auto_test_module.StepInstructions',
        total_points: float,
    ) -> float:
        data = test_instructions['data']
        assert isinstance(data, dict)

        res = 0.0

        code, stdout, stderr, time_spend = container.run_student_command(
            t.cast(str, data['program']),
            test_instructions['command_time_limit'],
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

    _MATCH_GROUP_NAME = 'amount_of_points'
    _FLOAT_REGEX = r'(?P<{}>(?:-\s*)?(?:1(?:\.0*)?|0(?:\.\d*)?))'.format(
        _MATCH_GROUP_NAME
    )

    @classmethod
    def _replace_custom_escape_code(cls, regex: str) -> t.Tuple[str, int]:
        r"""
        >>> C = _CustomOutput
        >>> C._FLOAT_REGEX = '<F_REGEX>'
        >>> f = C._replace_custom_escape_code
        >>> f(r'\f')
        ('<F_REGEX>', 1)
        >>> f(r'\\f')
        ('\\\\f', 0)
        >>> f(r'hello: \f')
        ('hello: <F_REGEX>', 1)
        >>> f(r'\f \b \f')
        ('<F_REGEX> \\b <F_REGEX>', 2)
        """
        res = []
        replacements = 0

        prev_back = False
        for char in regex:
            if prev_back and char == 'f':
                res.append(cls._FLOAT_REGEX)
                prev_back = False
                replacements += 1
            elif char == '\\' and prev_back:
                prev_back = False
                res.append('\\\\')
            elif char == '\\':
                assert not prev_back
                prev_back = True
            else:
                if prev_back:
                    res.append('\\')
                    prev_back = False
                res.append(char)

        return ''.join(res), replacements

    def validate_data(self, data: JSONType) -> None:
        """Validate if the given data is valid for a custom output test.
        """
        with get_from_map_transaction(
            ensure_json_dict(data, log_object=False), ensure_empty=True
        ) as [get, _]:
            program = get('program', str)
            regex = get('regex', str)

        _ensure_program(program)

        regex, groups = self._replace_custom_escape_code(regex)

        if groups < 1:
            raise APIException(
                'You have to have at least one \\f special sequence',
                f'The given regex "{regex}" did not contain \\f',
                APICodes.INVALID_PARAM, 400
            )
        elif groups > 1:
            helpers.add_warning(
                (
                    f'You added {groups} \\f in your regex, the behavior in'
                    ' the case that both \\f match is undefined.'
                ), APIWarnings.AMBIGUOUS_COMBINATION
            )

        try:
            re.compile(regex)
        except re.error as e:
            raise APIException(
                f'Compiling the regex failed: {e.msg}',
                'Compiling was not successful', APICodes.INVALID_PARAM, 400
            )

    @classmethod
    def _execute(
        cls,
        container: 'auto_test_module.StartedContainer',
        update_test_result: 'auto_test_module.UpdateResultFunction',
        test_instructions: 'auto_test_module.StepInstructions',
        total_points: float,
    ) -> float:
        state = AutoTestStepResultState.failed
        points = 0.0

        data = test_instructions['data']
        assert isinstance(data, dict)
        regex, _ = cls._replace_custom_escape_code(t.cast(str, data['regex']))

        code, stdout, stderr, time_spend = container.run_student_command(
            t.cast(str, data['program']),
            test_instructions['command_time_limit'],
        )

        logger.info(
            'Searching for points',
            regex=regex,
            stdout=stdout,
            stderr=stderr,
            code=code
        )

        if code == 0:
            try:
                match = re.search(regex, stdout, flags=re.REVERSE, timeout=2)
                if match:
                    points = between(
                        0.0, float(match.group(cls._MATCH_GROUP_NAME)), 1.0
                    )
                    state = AutoTestStepResultState.passed
                else:
                    code = -1
            except (ValueError, IndexError, TypeError):
                code = -2
            except TimeoutError:
                code = -3
                stderr += '\nSearching with the regex took too long'

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

    @staticmethod
    def get_amount_achieved_points(result: 'AutoTestStepResult') -> float:
        log: t.Dict = result.log if isinstance(result.log, dict) else {}
        return t.cast(float, log.get('points', 0)) * result.step.weight


@_register
class _CheckPoints(AutoTestStepBase):
    __mapper_args__ = {
        'polymorphic_identity': 'check_points',
    }

    @staticmethod
    def validate_weight(weight: float) -> None:
        """
        >>> c = _CheckPoints()
        >>> c.weight = 0
        >>> c.weight == 0
        True
        >>> c.weight = 1
        Traceback (most recent call last):
        ...
        psef.exceptions.APIException
        """
        if weight != 0:
            raise APIException(
                'The weight of a "check_points" step can only be 0',
                f'The given weight of "{weight}" is invalid',
                APICodes.INVALID_PARAM, 400
            )

    def validate_data(self, data: JSONType) -> None:
        """Validate if the given data is valid for a check_points test.
        """
        with get_from_map_transaction(
            ensure_json_dict(data, log_object=False), ensure_empty=True
        ) as [get, _]:
            get('min_points', numbers.Real)  # type: ignore

    @staticmethod
    def _execute(
        _: 'auto_test_module.StartedContainer',
        update_test_result: 'auto_test_module.UpdateResultFunction',
        test_instructions: 'auto_test_module.StepInstructions',
        total_points: float,
    ) -> float:
        data = test_instructions['data']
        assert isinstance(data, dict)

        if total_points >= t.cast(float, data['min_points']):
            update_test_result(AutoTestStepResultState.passed, {})
            return 0
        else:
            logger.warning(
                "Didn't score enough points", total_points=total_points
            )
            update_test_result(AutoTestStepResultState.failed, {})
            raise StopRunningStepsException('Not enough points')

    @staticmethod
    def get_amount_achieved_points(_: 'AutoTestStepResult') -> float:
        return 0


class AutoTestStepResult(Base, TimestampMixin, IdMixin):
    """This class represents the result of a single AutoTest step.
    """
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
        """The state of this result. Setting this might also change the
        ``started_at`` property.
        """
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
        """Get the amount of achieved points by this step result.
        """
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
        try:
            auth.ensure_can_view_autotest_step_details(self.step)
        except exceptions.PermissionException:
            res['log'] = self.step.remove_step_details(self.log)

        return res
