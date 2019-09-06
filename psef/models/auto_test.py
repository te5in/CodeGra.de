"""This module defines all models needed for auto tests.

SPDX-License-Identifier: AGPL-3.0-only
"""
import enum
import math
import uuid
import typing as t
import numbers
import datetime
import itertools

import structlog
from sqlalchemy import orm, sql
from sqlalchemy import func as sql_func
from sqlalchemy import distinct
from sqlalchemy_utils import UUIDType
from sqlalchemy.sql.expression import or_, and_, case, nullsfirst

import psef
import cg_json
from cg_sqlalchemy_helpers.mixins import IdMixin, UUIDMixin, TimestampMixin

from . import Base, MyQuery, DbColumn, db
from . import work as work_models
from . import auto_test_step as auto_test_step_models
from .. import auth
from .. import auto_test as auto_test_module
from .. import current_user
from ..helpers import NotEqualMixin
from ..registry import auto_test_handlers, auto_test_grade_calculators
from ..exceptions import (
    APICodes, APIException, PermissionException, InvalidStateException
)
from ..permissions import CoursePermission as CPerm

if t.TYPE_CHECKING:  # pragma: no cover
    # pylint: disable=unused-import
    from . import rubric as rubric_models
    from . import file as file_models
    from . import assignment as assignment_models

logger = structlog.get_logger()

GradeCalculator = t.Callable[[t.Sequence['rubric_models.RubricItem'], float],
                             'rubric_models.RubricItem']


class AutoTestSuite(Base, TimestampMixin, IdMixin):
    """This class represents a Suite (also known as category) in a AutoTest.
    """
    if t.TYPE_CHECKING:  # pragma: no cover
        query: t.ClassVar[MyQuery['AutoTestSuite']]
    __tablename__ = 'AutoTestSuite'
    id: int = db.Column('id', db.Integer, primary_key=True)

    rubric_row_id: int = db.Column(
        'rubric_row_id',
        db.Integer,
        db.ForeignKey('RubricRow.id'),
        nullable=False
    )
    rubric_row: 'rubric_models.RubricRow' = db.relationship(
        'RubricRow',
        foreign_keys=rubric_row_id,
        innerjoin=True,
    )

    network_disabled = db.Column(
        'network_disabled',
        db.Boolean,
        nullable=False,
        default=True,
        server_default='FALSE',
    )

    auto_test_set_id: int = db.Column(
        'auto_test_set_id',
        db.Integer,
        db.ForeignKey('AutoTestSet.id'),
        nullable=False
    )

    auto_test_set: 'AutoTestSet' = db.relationship(
        'AutoTestSet',
        foreign_keys=auto_test_set_id,
        back_populates='suites',
        lazy='joined',
        innerjoin=True,
    )

    steps = db.relationship(
        "AutoTestStepBase",
        back_populates="suite",
        cascade='all,delete,delete-orphan',
        order_by='AutoTestStepBase.order'
    )  # type: t.MutableSequence[auto_test_step_models.AutoTestStepBase]

    command_time_limit = db.Column(
        'command_time_limit', db.Float, nullable=True, default=None
    )

    def get_instructions(
        self, run: 'AutoTestRun'
    ) -> auto_test_module.SuiteInstructions:
        """Get the instructions to run this suite.
        """
        show_hidden = not run.is_continuous_feedback_run
        steps = [s for s in self.steps if show_hidden or not s.hidden]
        return {
            'id': self.id,
            'steps': [s.get_instructions() for s in steps],
            'network_disabled': self.network_disabled,
        }

    def __to_json__(self) -> t.Mapping[str, object]:
        return {
            'id': self.id,
            'steps': self.steps,
            'rubric_row': self.rubric_row,
            'network_disabled': self.network_disabled,
            'command_time_limit': self.command_time_limit,
        }

    def set_steps(self, steps: t.List['psef.helpers.JSONType']) -> None:
        """Set the steps of this suite.

        :param steps: The json data that should be parsed into the steps of
            this suite. They will be checked by this function.
        :returns: Nothing
        """
        new_steps = []
        for idx, step_data in enumerate(steps):
            with psef.helpers.get_from_map_transaction(
                psef.helpers.ensure_json_dict(step_data)
            ) as [get, opt]:

                step_id = opt('id', int, None)
                # data gets validated in the `step.update_data_from_json`
                data = get('data', dict)
                typ_str = get('type', str)
                name = get('name', str)
                hidden = get('hidden', bool)
                weight = t.cast(
                    float,
                    get('weight', numbers.Real)  # type: ignore
                )

            try:
                step_type = auto_test_handlers[typ_str]
            except KeyError:
                raise APIException(
                    'The given test type is not valid',
                    f'The given test type "{typ_str}" is not known',
                    APICodes.INVALID_PARAM, 400
                )

            if step_id is None:
                step = step_type()
                db.session.add(step)
            else:
                step = psef.helpers.get_or_404(step_type, step_id)
                assert isinstance(step, step_type)

            step.hidden = hidden
            step.order = idx
            step.name = name
            step.weight = weight

            step.update_data_from_json(data)
            new_steps.append(step)

        self.steps = new_steps


class AutoTestSet(Base, TimestampMixin, IdMixin):
    """This class represents a set (also known as level) of an AutoTest.
    """
    if t.TYPE_CHECKING:  # pragma: no cover
        query: t.ClassVar[MyQuery['AutoTestSet']]
    __tablename__ = 'AutoTestSet'

    id: int = db.Column('id', db.Integer, primary_key=True)
    stop_points: float = db.Column(
        'stop_points', db.Float, nullable=False, default=0
    )
    auto_test_id: int = db.Column(
        'auto_test_id',
        db.Integer,
        db.ForeignKey('AutoTest.id'),
        nullable=False
    )

    auto_test: 'AutoTest' = db.relationship(
        'AutoTest',
        foreign_keys=auto_test_id,
        back_populates='sets',
        lazy='joined',
        innerjoin=True,
    )

    suites = db.relationship(
        "AutoTestSuite",
        back_populates="auto_test_set",
        cascade='all,delete,delete-orphan',
        order_by='AutoTestSuite.created_at'
    )  # type: t.MutableSequence[AutoTestSuite]

    def get_instructions(
        self, run: 'AutoTestRun'
    ) -> auto_test_module.SetInstructions:
        """Get the instructions to run this set.
        """
        return {
            'id': self.id,
            'suites': [s.get_instructions(run) for s in self.suites],
            'stop_points': self.stop_points,
        }

    def __to_json__(self) -> t.Mapping[str, object]:
        return {
            'id': self.id,
            'suites': self.suites,
            'stop_points': self.stop_points,
        }


class AutoTestResult(Base, TimestampMixin, IdMixin, NotEqualMixin):
    """The result for a single submission (:class:`.work_models.Work`) of a
    :class:`.AutoTestRun`.
    """
    __tablename__ = 'AutoTestResult'

    if t.TYPE_CHECKING:  # pragma: no cover
        query: t.ClassVar[MyQuery['AutoTestResult']]

    auto_test_run_id: int = db.Column(
        'auto_test_run_id',
        db.Integer,
        db.ForeignKey('AutoTestRun.id'),
        nullable=False
    )

    run: 'AutoTestRun' = db.relationship(
        'AutoTestRun',
        foreign_keys=auto_test_run_id,
        back_populates='results',
        lazy='select',
        innerjoin=True,
    )

    auto_test_runner_id: t.Optional[uuid.UUID] = db.Column(
        'auto_test_runner_id',
        UUIDType,
        db.ForeignKey('AutoTestRunner.id'),
        nullable=True,
    )

    runner: t.Optional['AutoTestRunner'] = db.relationship(
        'AutoTestRunner',
        foreign_keys=auto_test_runner_id,
        lazy='selectin',
    )

    setup_stdout: t.Optional[str] = orm.deferred(
        db.Column(
            'setup_stdout',
            db.Unicode,
            default=None,
        )
    )

    started_at: t.Optional[datetime.datetime] = db.Column(
        'started_at', db.DateTime, default=None, nullable=True
    )

    setup_stderr: t.Optional[str] = orm.deferred(
        db.Column(
            'setup_stderr',
            db.Unicode,
            default=None,
        )
    )

    step_results = db.relationship(
        'AutoTestStepResult',
        back_populates='result',
        cascade='all,delete,delete-orphan',
        order_by='AutoTestStepResult.created_at',
        lazy='selectin',
    )  # type: t.MutableSequence[auto_test_step_models.AutoTestStepResult]

    _state = db.Column(
        'state',
        db.Enum(auto_test_step_models.AutoTestStepResultState),
        default=auto_test_step_models.AutoTestStepResultState.not_started,
        nullable=False,
    )

    work_id: int = db.Column(
        'work_id',
        db.Integer,
        db.ForeignKey('Work.id', ondelete='CASCADE'),
        nullable=False,
    )
    work = db.relationship(
        'Work', foreign_keys=work_id, lazy='selectin'
    )  # type: work_models.Work

    def __eq__(self, other: object) -> bool:
        if isinstance(other, AutoTestResult):
            return other.id == self.id
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.id)

    @property
    def state(self) -> auto_test_step_models.AutoTestStepResultState:
        """Get the state of this result

        >>> called = False
        >>> def fun(_):
        ...  global called
        ...  called = True
        >>> psef.tasks.adjust_amount_runners = fun
        >>> r = AutoTestResult(run=AutoTestRun())
        >>> not_set = object()
        >>> r.started_at = not_set
        >>> r.state = auto_test_step_models.AutoTestStepResultState.running
        >>> isinstance(r.started_at, datetime.datetime)
        True
        >>> called
        True
        >>> r.state = 6
        >>> r.started_at is None
        True
        >>> r.started_at = not_set
        >>> r.state = 6
        >>> r.started_at is not_set
        True
        """
        return self._state

    @state.setter
    def state(
        self, new_state: auto_test_step_models.AutoTestStepResultState
    ) -> None:
        if new_state == self._state:
            return

        self._state = new_state
        if new_state == auto_test_step_models.AutoTestStepResultState.running:
            self.started_at = datetime.datetime.utcnow()
            psef.tasks.adjust_amount_runners(self.run.id)
        else:
            self.started_at = None

    @property
    def passed(self) -> bool:
        """Has this state passed?
        """
        return (
            self.state == auto_test_step_models.AutoTestStepResultState.passed
        )

    def clear(self) -> None:
        """Clear this result and set it state back to ``not_started``.

        .. note:: This also clears the rubric
        """
        self.step_results = []
        self.state = auto_test_step_models.AutoTestStepResultState.not_started
        self.setup_stderr = None
        self.setup_stdout = None
        self.runner = None
        self.clear_rubric()

    def clear_rubric(self) -> None:
        """Clear all the rubric categories connected to this AutoTest for this
        result.

        :returns: Nothing
        """
        own_rubric_rows = set(
            suite.rubric_row_id for suite in self.run.auto_test.all_suites
        )

        self.work.selected_items = [
            i for i in self.work.selected_items
            if i.rubricrow_id not in own_rubric_rows
        ]
        self.work.set_grade(grade_origin=work_models.GradeOrigin.auto_test)

    def update_rubric(self) -> None:
        """Update the rubric of the connected submission according to this
        AutoTest result.

        .. note:: This might pass back the grade to the LMS if required.
        """
        old_selected_items = set(self.work.selected_items)
        new_items = {i.rubricrow_id: i for i in self.work.selected_items}
        changed_item = False

        for suite in self.run.auto_test.all_suites:
            got, possible = self.get_amount_points_in_suites(suite)
            percentage = got / possible
            items = suite.rubric_row.items
            assert self.run.auto_test.grade_calculator is not None
            new_item = self.run.auto_test.grade_calculator(items, percentage)

            if new_item not in old_selected_items:
                new_items[suite.rubric_row_id] = new_item
                changed_item = True

        if not changed_item:
            return

        self.work.selected_items = list(new_items.values())
        self.work.set_grade(grade_origin=work_models.GradeOrigin.auto_test)

    def get_amount_points_in_suites(self, *suites: 'AutoTestSuite'
                                    ) -> t.Tuple[float, float]:
        """Get the amount of points in the given suites, and how many points
        where achieved.

        :param suites: The suites to calculate the amount of points for.
        :returns: A tuple where the first value is the amount of points
            achieved in the given suites, and the second value is the amount of
            points possible in the given suites.
        """
        steps = list(
            itertools.chain.from_iterable(suite.steps for suite in suites)
        )

        step_ids = set(step.id for step in steps)
        possible = sum(step.weight for step in steps)
        achieved = sum(
            step_result.achieved_points for step_result in self.step_results
            if step_result.auto_test_step_id in step_ids
        )

        return achieved, possible

    def __to_json__(self) -> t.Mapping[str, object]:
        """Convert this result to a json object.
        """

        points_achieved, _ = self.get_amount_points_in_suites(
            *self.run.auto_test.all_suites
        )
        return {
            'id': self.id,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at and self.started_at.isoformat(),
            'work_id': self.work_id,
            'state': self.state.name,
            'points_achieved': points_achieved,
        }

    def __extended_to_json__(self) -> t.Mapping[str, object]:
        approx_before: t.Optional[int] = None
        not_started = auto_test_step_models.AutoTestStepResultState.not_started
        if self.state == not_started:
            approx_before = 0
            for result in self.run.results:
                if result == self:
                    break
                elif result.state == not_started:
                    approx_before += 1
            else:
                logger.warning('Result not found', exc_info=True)
                approx_before = None

        return {
            **self.__to_json__(),
            'setup_stdout': self.setup_stdout,
            'setup_stderr': self.setup_stderr,
            'step_results': self.step_results,
            'approx_waiting_before': approx_before,
        }


@enum.unique
class AutoTestRunState(cg_json.SerializableEnum, enum.Enum):
    """This enum represents the state a single run is in.

    .. warning::

        When you change this enum make sure you update the properties of
        :class:`.AutoTestRun` too as they define some helper functions for this
        enum.
    """
    waiting_for_runner = 1
    starting = 2
    running = 3
    done = 4
    timed_out = 5
    crashed = 6
    changing_runner = 7


class AutoTestRunner(Base, TimestampMixin, UUIDMixin, NotEqualMixin):
    """This class represents the runner of a :class:`.AutoTestRun`.

    A single run might have multiple runners, as a runner might crash and in
    this case it is replaced by a new runner.
    """
    if t.TYPE_CHECKING:  # pragma: no cover
        query: t.ClassVar[MyQuery['AutoTestRunner']]

    __tablename__ = 'AutoTestRunner'

    _ipaddr: str = db.Column('ipaddr', db.Unicode, nullable=False)

    last_heartbeat: datetime.datetime = db.Column(
        'last_heartbeat', db.DateTime, default=datetime.datetime.utcnow
    )

    _job_id: t.Optional[str] = db.Column('job_id', db.Unicode)

    run_id: t.Optional[int] = db.Column(
        'run_id',
        db.Integer,
        db.ForeignKey('AutoTestRun.id'),
        nullable=True,
        default=None,
    )

    run: t.Optional['AutoTestRun'] = db.relationship(
        'AutoTestRun',
        foreign_keys=run_id,
        back_populates='runners',
    )

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AutoTestRunner):
            return NotImplemented
        return self.id == other.id

    @property
    def job_id(self) -> str:
        """Get the job id of this runner.

        >>> AutoTestRunner().job_id.startswith('INVALID-')
        True
        >>> AutoTestRunner(_job_id='hello').job_id
        'hello'
        """
        return self._job_id or f'INVALID-{uuid.uuid4().hex}'

    @property
    def ipaddr(self) -> str:
        """The ip address of this runner."""
        return self._ipaddr

    @classmethod
    def create(
        cls,
        ipaddr: str,
        run: 'AutoTestRun',
    ) -> 'AutoTestRunner':
        """Create an :class:`.AutoTestRunner`.

        :param ipdaddr: The ip address of this runner.
        :param run: The run of this runner.
        """
        return cls(_ipaddr=ipaddr, _job_id=run.get_job_id(), run=run)


class AutoTestRun(Base, TimestampMixin, IdMixin):
    """This class represents a single run of an AutoTest configuration.

    At the moment each AutoTest will always only have one AutoTestRun.
    """
    __tablename__ = 'AutoTestRun'

    if t.TYPE_CHECKING:  # pragma: no cover
        query: t.ClassVar[MyQuery['AutoTestRun']]

    auto_test_id: int = db.Column(
        'auto_test_id',
        db.Integer,
        db.ForeignKey('AutoTest.id'),
        nullable=False
    )

    setup_stdout: t.Optional[str] = orm.deferred(
        db.Column(
            'setup_stdout',
            db.Unicode,
            default=None,
        )
    )

    setup_stderr: t.Optional[str] = orm.deferred(
        db.Column(
            'setup_stderr',
            db.Unicode,
            default=None,
        )
    )

    runners: t.List['AutoTestRunner'] = db.relationship(
        'AutoTestRunner', back_populates='run'
    )

    auto_test: 'AutoTest' = db.relationship(
        'AutoTest',
        foreign_keys=auto_test_id,
        back_populates='_runs',
        lazy='joined',
        innerjoin=True,
    )

    results = db.relationship(
        'AutoTestResult',
        back_populates='run',
        cascade='all,delete',
        order_by='AutoTestResult.created_at'
    )  # type: t.MutableSequence[AutoTestResult]

    _state = db.Column(
        'state',
        db.Enum(AutoTestRunState),
        default=AutoTestRunState.waiting_for_runner,
        nullable=False,
    )
    started_date: t.Optional[datetime.datetime] = db.Column(
        'started_date', db.DateTime, nullable=True, default=None
    )
    kill_date: t.Optional[datetime.datetime] = db.Column(
        'kill_date', db.DateTime, nullable=True, default=None
    )

    _job_number = db.Column('job_number', db.Integer, default=0)
    _job_id: uuid.UUID = db.Column('job_id', UUIDType, default=uuid.uuid4)
    runners_requested: int = db.Column(
        'runners_requested',
        db.Integer,
        default=0,
        server_default='0',
        nullable=False,
    )

    is_continuous_feedback_run: bool = db.Column(
        'is_continuous_feedback_run',
        db.Boolean,
        default=False,
        nullable=False,
        server_default=sql.expression.false(),
    )

    def increment_job_id(self) -> None:
        """Increment the job id of this runner.

        This should be done when creating a new runner for this run, so we can
        track each runner by this id. This is different from creating a
        completely new job id, as this will make sure we keep the same base job
        id.
        """
        cur_number = self._job_number or 0
        self._job_number = cur_number + 1

    def get_job_id(self) -> str:
        return f'{self._job_id.hex}-{self._job_number or 0}'

    @property
    def active(self) -> bool:
        """Check if this run is active.
        """
        return self.state in {AutoTestRunState.running}

    @property
    def finished(self) -> bool:
        """Check if the state of this run is in one of the states we consider
        finished.
        """
        return self.state in {
            AutoTestRunState.done,
            AutoTestRunState.timed_out,
            AutoTestRunState.crashed,
        }

    @property
    def state(self) -> AutoTestRunState:
        """Get the state of this run.
        """
        return self._state

    @state.setter
    def state(self, new_state: AutoTestRunState) -> None:
        assert isinstance(new_state, AutoTestRunState)

        if self.is_continuous_feedback_run:
            if new_state.value > AutoTestRunState.running.value:  # pragma: no cover
                # This should never happen, as it should be handled in the
                # internal api.
                start_new = self.stop_runners(
                    self.runners,
                ) or db.session.query(
                    self.get_results_to_run().exists(),
                ).scalar()

                if start_new:
                    psef.tasks.adjust_amount_runners(self.id)
            else:
                self._state = new_state
        else:
            self._state = new_state

            if new_state == AutoTestRunState.done:
                for result in self.results:
                    result.update_rubric()

            if self.finished:
                self.stop_runners(self.runners)

    def stop_runners(self, runners: t.List[AutoTestRunner]) -> bool:
        """Stop the runner of this run.

        This also prepares the run to be migrated to a new runner.
        """
        assert all(runner in self.runners for runner in runners)
        all_deleted = len(runners) == len(self.runners)
        total_result = False

        for runner in runners:
            self.runners.remove(runner)
            runner.run_id = None
            psef.tasks.notify_broker_kill_single_runner(self.id, runner.id.hex)
            # This function has a side effect so make sure short circuiting
            # doesn't cause the function not to be called.
            result = self._clear_non_passed_results(runner)
            total_result = result or total_result

        if all_deleted:
            psef.tasks.notify_broker_end_of_job(self.get_job_id())
            self.runners_requested = 0
            self.increment_job_id()

        db.session.flush()
        return result

    def get_broker_metadata(self) -> t.Mapping[str, object]:
        """Get metadata that is useful for the broker of this run.
        """
        assig = self.auto_test.assignment
        return {
            'course': {
                'id': assig.course.id,
                'name': assig.course.name,
            },
            'assignment': {
                'id': assig.id,
                'name': assig.name,
            },
            'created_at': self.created_at.isoformat(),
            'id': self.id,
            'type': 'CF' if self.is_continuous_feedback_run else 'AT',
        }

    def _clear_non_passed_results(self, runner: AutoTestRunner) -> bool:
        any_cleared = False

        for result in self.results:
            if (
                not result.passed and
                (result.runner is None or result.runner == runner)
            ):
                result.clear()
                any_cleared = True

        return any_cleared

    def get_amount_needed_runners(self) -> int:
        """Get the amount of runners this run needs.
        """
        amount_not_done = self.get_results_to_run().count()
        return math.ceil(
            amount_not_done / psef.app.config['AUTO_TEST_MAX_JOBS_PER_RUNNER']
        )

    @classmethod
    def get_runs_that_need_runners(cls) -> t.List['AutoTestRun']:
        """Get all runs that need more runners.

        This function gets all runs that have fewer runners than they should,
        which is calculated using the amount of results that have not yet
        started.
        """
        ARR = AutoTestRunner
        ARS = AutoTestResult

        amount_results = sql_func.count(distinct(ARS.id))
        amount_runners = sql_func.count(distinct(ARR.id))

        runs = db.session.query(cls).join(
            ARS,
            and_(
                ARS.auto_test_run_id == cls.id,
                (
                    ARS._state ==  # pylint: disable=protected-access
                    auto_test_step_models.AutoTestStepResultState.not_started
                ),
            ),
        ).join(
            ARR,
            ARR.run_id == cls.id,
            isouter=True,
        ).having(
            or_(
                amount_runners == 0, amount_results / amount_runners >
                psef.app.config['AUTO_TEST_MAX_JOBS_PER_RUNNER']
            )
        ).group_by(cls.id).order_by(
            nullsfirst(
                (
                    amount_results / case(
                        [(amount_runners == 0, None)],
                        else_=amount_runners,
                    )
                ).desc()
            )
        ).options(orm.noload(cls.auto_test))

        return runs.all()

    def get_results_to_run(self) -> MyQuery[AutoTestResult]:
        """Get a query to get the :py:class:`.AutoTestResult` items that still
            need to be run.
        """
        # We make sure we only give results we actually want run, so only those
        # of the newest submissions.
        latest_ids = self.auto_test.assignment.get_from_latest_submissions(
            work_models.Work.id
        )

        return db.session.query(AutoTestResult).filter_by(
            _state=auto_test_step_models.AutoTestStepResultState.not_started,
            auto_test_run_id=self.id,
        ).filter(
            t.cast(DbColumn[int], AutoTestResult.work_id).in_(latest_ids)
        ).order_by(AutoTestResult.created_at)

    def add_active_runner(
        self,
        runner_ipaddr: str,
    ) -> AutoTestRunner:
        """Start this run.

        This means setting the ``started_date``, creating a runner object for
        this run, and scheduling some tasks that will kill the runner after
        some period of time.

        .. note::

            To start an entire run you should use :meth:`.AutoTest.start_run`.

        :param runner_ipaddr: The ip address of the runner that will perform
            this run. This is used for authentication purposes.
        """
        # This run was not started before this runner, so set all the auxiliary
        # data.
        start_sanity_tasks = False
        if self.started_date is None:
            self.started_date = datetime.datetime.utcnow()
            # Continuous feedback runs don't get killed because of time, so
            # don't set this data.
            if not self.is_continuous_feedback_run:
                start_sanity_tasks = True
                max_duration = datetime.timedelta(
                    minutes=psef.app.config['AUTO_TEST_MAX_TIME_TOTAL_RUN'],
                )
                now = datetime.datetime.utcnow()
                self.kill_date = now + max_duration
        runner = AutoTestRunner.create(runner_ipaddr, run=self)
        db.session.add(runner)
        db.session.flush()

        @psef.helpers.callback_after_this_request
        def __start_tasks() -> None:
            if start_sanity_tasks:
                psef.tasks.notify_slow_auto_test_run(
                    (self.id, ), eta=now + (max_duration / 2)
                )
                psef.tasks.stop_auto_test_run((self.id, ), eta=self.kill_date)

            psef.tasks.check_heartbeat_auto_test_run((runner.id.hex, ))

        return runner

    def get_instructions(
        self, for_runner: AutoTestRunner
    ) -> auto_test_module.RunnerInstructions:
        """Get the instructions to run this AutoTestRun.
        """
        results = [r for r in self.results if not r.passed]

        return {
            'runner_id': str(for_runner.id),
            'run_id': self.id,
            'auto_test_id': self.auto_test_id,
            'result_ids': [r.id for r in results],
            'student_ids': [r.work.user_id for r in results],
            'sets': [s.get_instructions(self) for s in self.auto_test.sets],
            'fixtures': [(f.name, f.id) for f in self.auto_test.fixtures],
            'setup_script': self.auto_test.setup_script,
            'heartbeat_interval':
                psef.app.config['AUTO_TEST_HEARTBEAT_INTERVAL'],
            'run_setup_script': self.auto_test.run_setup_script,
            'is_continuous_run': self.is_continuous_feedback_run,
        }

    def __to_json__(self) -> t.Mapping[str, object]:
        return {
            'id': self.id,
            'created_at': self.created_at.isoformat(),
            'state': self.state.name,
            'is_continuous': self.is_continuous_feedback_run,
        }

    def __extended_to_json__(self) -> t.Mapping[str, object]:
        results = []
        for result in self.results:
            try:
                auth.ensure_can_view_autotest_result(result)
            except PermissionException:
                continue
            else:
                results.append(result)

        # TODO: Check permissions for setup_stdout/setup_stderr
        return {
            **self.__to_json__(),
            'results': results,
            'setup_stdout': self.setup_stdout or '',
            'setup_stderr': self.setup_stderr or '',
        }

    def delete_and_clear_rubric(self) -> None:
        """Delete this AutoTestRun and clear all the results and rubrics.
        """
        for result in self.results:
            result.clear_rubric()
        db.session.delete(self)


@auto_test_grade_calculators.register('full')
def _full_grade_calculator(
    items: t.Sequence['rubric_models.RubricItem'], percentage: float
) -> 'rubric_models.RubricItem':
    """Calculate a grade based on the ``full`` policy.

    >>> _full_grade_calculator([0,1,2,3], 0.25)
    0
    >>> _full_grade_calculator([0,1,2,3], 0.5)
    1
    >>> _full_grade_calculator([0,1,2,3], 0.75)
    2
    >>> _full_grade_calculator([0,1,2,3], 1)
    3
    >>> _full_grade_calculator([0,1,2,3], 0.9)
    2
    >>> _full_grade_calculator([0,1,2,3], 0)
    0
    >>> _full_grade_calculator([0,1,2,3], 0.1)
    0
    """
    return items[max(0, int(len(items) * percentage) - 1)]


@auto_test_grade_calculators.register('partial')
def _partial_grade_calculator(
    items: t.Sequence['rubric_models.RubricItem'], percentage: float
) -> 'rubric_models.RubricItem':
    """Calculate a grade based on the ``partial`` policy.

    >>> _partial_grade_calculator([0,1,2,3], 1)
    3
    >>> _partial_grade_calculator([0,1,2,3], 0.9)
    3
    >>> _partial_grade_calculator([0,1,2,3], 0)
    0
    >>> _partial_grade_calculator([0,1,2,3], 0.1)
    0
    >>> _partial_grade_calculator([0,1,2,3], 0.25)
    1
    """
    return items[min(len(items) - 1, int(len(items) * percentage))]


class AutoTest(Base, TimestampMixin, IdMixin):
    """This class represents a auto test.

    A group set is a single wrapper over all groups. Every group is part of a
    group set. The group set itself is connected to a single course and zero or
    more assignments in this course.

    :ivar minimum_size: The minimum size of that group should have before it
        can be used to submit a submission.
    :ivar maximum_size: The maximum amount of members a group can ever have.
    """
    if t.TYPE_CHECKING:  # pragma: no cover
        query: t.ClassVar[MyQuery['AutoTest']]
    __tablename__ = 'AutoTest'

    id: int = db.Column('id', db.Integer, primary_key=True)

    assignment: 'assignment_models.Assignment' = db.relationship(
        'Assignment',
        back_populates='auto_test',
        innerjoin=True,
        uselist=False
    )
    sets = db.relationship(
        "AutoTestSet",
        back_populates="auto_test",
        cascade='all,delete,delete-orphan',
        order_by='AutoTestSet.created_at'
    )  # type: t.MutableSequence[AutoTestSet]

    _runs = db.relationship(
        "AutoTestRun",
        back_populates="auto_test",
        cascade='all,delete,delete-orphan',
        order_by='AutoTestRun.created_at'
    )  # type: t.MutableSequence[AutoTestRun]

    @property
    def test_run(self) -> t.Optional[AutoTestRun]:
        """The final run of this AutoTest.

        :returns: The final run of this AutoTest or ``None`` if there is none.
        """
        return next(
            (r for r in self._runs if not r.is_continuous_feedback_run), None
        )

    @property
    def continuous_feedback_run(self) -> t.Optional[AutoTestRun]:
        """The continuous feedback run of this AutoTest.

        :returns: The continuous feedback run of this AutoTest or ``None`` if
            there is none.
        """
        return next(
            (r for r in self._runs if r.is_continuous_feedback_run), None
        )

    def get_all_runs(self) -> t.Sequence[AutoTestRun]:
        return self._runs

    fixtures = db.relationship(
        'AutoTestFixture',
        back_populates="auto_test",
        cascade='all,delete',
        order_by="AutoTestFixture.name"
    )  # type: t.MutableSequence[file_models.AutoTestFixture]

    setup_script: str = db.Column(
        'setup_script', db.Unicode, nullable=False, default=''
    )
    run_setup_script: str = db.Column(
        'run_setup_script', db.Unicode, nullable=False, default=''
    )
    finalize_script: str = db.Column(
        'finalize_script', db.Unicode, nullable=False, default=''
    )

    _grade_calculation: t.Optional[str] = db.Column(
        'grade_calculation',
        db.Enum(
            *auto_test_grade_calculators.keys(), name='grade_calculation_enum'
        ),
        nullable=True,
        default=None,
    )

    def ensure_no_runs(self) -> None:
        """Ensure that this AutoTest has no runs.

        :raises APIException: If the AutoTest has one or more runs.
        """
        if self.test_run is not None:
            raise APIException(
                'You cannot update an AutoTest which has runs',
                f'The given AutoTest "{self.id}" has a run',
                APICodes.INVALID_STATE, 409
            )

    @property
    def grade_calculator(self) -> t.Optional[GradeCalculator]:
        """Get the grade calculator for this AutoTest.

        >>> AutoTest().grade_calculator is None
        True
        """
        if self._grade_calculation is None:
            return None
        return auto_test_grade_calculators.get(self._grade_calculation)

    @grade_calculator.setter
    def grade_calculator(self, new_val: GradeCalculator) -> None:
        """Set the grade calculator for this AutoTest.

        This should be a registered grade calculator.

        :param new_val: The new grade calculator.
        """
        key = auto_test_grade_calculators.find(new_val, None)
        assert key is not None
        self._grade_calculation = key

    def _ensure_can_start_run(self) -> None:
        if self.grade_calculator is None:
            raise InvalidStateException(
                'This AutoTest has no grade_calculation set, but this options'
                ' is required.'
            )

        if not self.sets:
            raise InvalidStateException(
                'This AutoTest has no sets, so it cannot be started'
            )

        if next(self.all_suites, None) is None:
            raise InvalidStateException(
                'This AutoTest has no suites, so it cannot be started'
            )

        if any(not s.steps for s in self.all_suites):
            raise InvalidStateException(
                'This AutoTest has no steps in some suites, so it cannot be'
                ' started'
            )

        if any(sum(st.weight for st in s.steps) <= 0 for s in self.all_suites):
            raise InvalidStateException(
                'This AutoTest has zero amount of points possible in some'
                ' suites, so it cannot be started'
            )

    def start_test_run(self) -> AutoTestRun:
        """Start this AutoTest run.

        This function checks if the AutoTest is in a state where a run can be
        started, and if this is the case it starts the run. It also schedules a
        task to notify our broker that we need a runner. The changes to the
        database are not committed!
        """
        self._ensure_can_start_run()
        if self.test_run is not None:
            raise APIException(
                'You cannot start an AutoTest which has runs',
                f'The given AutoTest "{self.id}" has a run',
                APICodes.INVALID_STATE, 409
            )

        run = AutoTestRun()
        self._runs.append(run)
        db.session.flush()

        results = [
            AutoTestResult(work_id=work_id, auto_test_run_id=run.id)
            for work_id, in
            self.assignment.get_from_latest_submissions(work_models.Work.id)
        ]
        db.session.bulk_save_objects(results)
        psef.helpers.callback_after_this_request(
            lambda: psef.tasks.
            notify_broker_of_new_job(run.id, run.get_amount_needed_runners())
        )
        return run

    def start_continuous_feedback_run(self) -> AutoTestRun:
        """Start a continuous feedback run for this AutoTest.
        """
        self._ensure_can_start_run()
        if self.continuous_feedback_run:
            raise APIException(
                'You cannot start an AutoTest which has runs',
                f'The given AutoTest "{self.id}" has a run',
                APICodes.INVALID_STATE, 409
            )

        run = AutoTestRun(is_continuous_feedback_run=True)
        self._runs.append(run)
        return run

    @property
    def all_suites(self) -> t.Iterator[AutoTestSuite]:
        """Get all the suites from this AutoTest as an iterator.
        """
        return itertools.chain.from_iterable(s.suites for s in self.sets)

    def add_to_continuous_feedback(self, work: 'work_models.Work') -> bool:
        """Add the given work to the continuous feedback run.

        This function only does something if there is an continuous feedback
        run.

        :param work: The work to add to the continuous feedback run.
        :returns: ``True`` if the work was added to the continuous feedback
            run.

        .. warning::

            This function changes the session if it returns ``True``, so a
            commit is necessary in that case.
        """
        run = self.continuous_feedback_run
        # Do not start if there is a normal test run, as that run will test
        # everything.
        if run is None or self.test_run is not None:
            return False

        run_id = run.id

        psef.helpers.callback_after_this_request(
            lambda: psef.tasks.adjust_amount_runners(run_id)
        )

        result = AutoTestResult(work=work, auto_test_run_id=run.id)
        db.session.add(result)
        return True

    def __to_json__(self) -> t.Mapping[str, object]:
        """Covert this AutoTest to json.
        """
        runs: t.Sequence[AutoTestRun] = []

        if self.assignment.is_done or current_user.has_permission(
            CPerm.can_see_grade_before_open, self.assignment.course_id
        ):
            runs = self._runs
        elif self.continuous_feedback_run is not None:
            runs = [self.continuous_feedback_run]

        return {
            'id': self.id,
            'fixtures': self.fixtures,
            'setup_script': self.setup_script,
            'run_setup_script': self.run_setup_script,
            'finalize_script': self.finalize_script,
            'grade_calculation': self._grade_calculation,
            'sets': self.sets,
            'assignment_id': self.assignment.id,
            'runs': runs,
        }
