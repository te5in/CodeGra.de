"""This module defines all models needed for auto tests.

SPDX-License-Identifier: AGPL-3.0-only
"""
import os
import enum
import uuid
import typing as t
import numbers
import datetime
import itertools

import structlog
from sqlalchemy import orm
from sqlalchemy.types import JSON
from sqlalchemy_utils import UUIDType

import psef

from . import Base, DbColumn, db
from . import file as file_models
from . import work as work_models
from . import rubric as rubric_models
from . import _MyQuery
from . import assignment as assignment_models
from . import auto_test_step as auto_test_step_models
from .. import auth
from .. import auto_test as auto_test_module
from .. import exceptions, current_user
from .mixins import IdMixin, UUIDMixin, TimestampMixin
from ..exceptions import APICodes, APIException
from ..permissions import CoursePermission as CPerm

if t.TYPE_CHECKING:
    from . import user as user_models

logger = structlog.get_logger()


class AutoTestSuite(Base, TimestampMixin, IdMixin):
    if t.TYPE_CHECKING:  # pragma: no cover
        query: t.ClassVar[_MyQuery['AutoTestSuite']]
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

    def get_instructions(self) -> auto_test_module.SuiteInstructions:
        return {
            'id': self.id,
            'steps': [s.get_instructions() for s in self.steps],
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


class AutoTestSet(Base, TimestampMixin, IdMixin):
    if t.TYPE_CHECKING:  # pragma: no cover
        query: t.ClassVar[_MyQuery['AutoTestSet']]
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
        "AutoTestSuite", back_populates="auto_test_set", cascade='all,delete'
    )  # type: t.MutableSequence[AutoTestSuite]

    def get_instructions(self) -> auto_test_module.SetInstructions:
        return {
            'id': self.id,
            'suites': [s.get_instructions() for s in self.suites],
            'stop_points': self.stop_points,
        }

    def __to_json__(self) -> t.Mapping[str, object]:
        return {
            'id': self.id,
            'suites': self.suites,
            'stop_points': self.stop_points,
        }


class AutoTestResult(Base, TimestampMixin, IdMixin):
    __tablename__ = 'AutoTestResult'

    if t.TYPE_CHECKING:  # pragma: no cover
        query: t.ClassVar[_MyQuery['AutoTestResult']]

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
        lazy='joined',
        innerjoin=True,
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
        order_by='AutoTestStepResult.created_at'
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
        'Work', foreign_keys=work_id
    )  # type: work_models.Work

    @property
    def state(self) -> auto_test_step_models.AutoTestStepResultState:
        return self._state

    @state.setter
    def state(self, s: auto_test_step_models.AutoTestStepResultState) -> None:
        if s == self._state:
            return

        self._state = s
        if s == auto_test_step_models.AutoTestStepResultState.running:
            self.started_at = datetime.datetime.utcnow()
        else:
            self.started_at = None

    @property
    def passed(self) -> bool:
        return self.state == auto_test_step_models.AutoTestStepResultState.passed

    def clear(self) -> None:
        self.step_results = []
        self.state = auto_test_step_models.AutoTestStepResultState.not_started
        self.setup_stderr = None
        self.setup_stdout = None

    def clear_rubric(self) -> None:
        own_rubric_rows = set(
            suite.rubric_row_id for suite in self.run.auto_test.all_suites
        )

        self.work.selected_items = [
            i for i in self.work.selected_items
            if i.rubricrow_id not in own_rubric_rows
        ]
        self.work.set_grade(grade_origin=work_models.GradeOrigin.auto_test)

    def update_rubric(self) -> None:
        old_selected_items = set(self.work.selected_items)
        new_items = []
        updated_rubric_row_ids = set()

        for suite in self.run.auto_test.all_suites:
            got, possible = self.get_amount_points_in_suites(suite)
            percentage = got / possible
            items = suite.rubric_row.items
            new_item = items[-1 if percentage ==
                             1 else int(len(items) * percentage)]
            if new_item in old_selected_items:
                continue

            new_items.append(new_item)
            updated_rubric_row_ids.add(suite.rubric_row_id)

        if not new_items:
            return

        self.work.selected_items = [
            *new_items,
            *[
                i for i in self.work.selected_items
                if i.rubricrow_id not in updated_rubric_row_ids
            ],
        ]
        self.work.set_grade(grade_origin=work_models.GradeOrigin.auto_test)

    def get_amount_points_in_suites(self, *suites: 'AutoTestSuite'
                                    ) -> t.Tuple[float, float]:
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
        points_achieved, _ = self.get_amount_points_in_suites(
            *self.run.auto_test.all_suites
        )
        return {
            'id': self.id,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at and self.started_at.isoformat(),
            'work': self.work,
            'state': self.state.name,
            'points_achieved': points_achieved,
        }

    def __extended_to_json__(self) -> t.Mapping[str, object]:
        return {
            **self.__to_json__(),
            'setup_stdout': self.setup_stdout,
            'setup_stderr': self.setup_stderr,
            'step_results': self.step_results,
        }


class AutoTestRunState(enum.Enum):
    waiting_for_runner = enum.auto()
    starting = enum.auto()
    running = enum.auto()
    done = enum.auto()
    timed_out = enum.auto()
    crashed = enum.auto()
    changing_runner = enum.auto()


class AutoTestAfterRunState(enum.Enum):
    not_called = enum.auto()
    calling = enum.auto()
    called = enum.auto()


class AutoTestRunner(Base, TimestampMixin, UUIDMixin):
    if t.TYPE_CHECKING:  # pragma: no cover
        query: t.ClassVar[_MyQuery['AutoTestRunner']]

    __tablename__ = 'AutoTestRunner'

    _type: str = db.Column(
        'type',
        db.Enum(
            *auto_test_module.auto_test_runners.keys(),
            name='autotestrunnertype'
        ),
        nullable=False
    )

    _ipaddr: str = db.Column('ipaddr', db.Unicode, nullable=False)

    last_heartbeat: datetime.datetime = db.Column(
        'last_heartbeat', db.DateTime, default=datetime.datetime.utcnow
    )

    #: Is this runner completely finished. So is the `after_run` method called.
    after_state = db.Column(
        'after_run',
        db.Enum(AutoTestAfterRunState),
        nullable=False,
        default=AutoTestAfterRunState.not_called,
        server_default='called',
    )

    run: t.Optional['AutoTestRun'] = db.relationship(
        "AutoTestRun",
        back_populates="runner",
        cascade='all,delete',
        order_by='AutoTestRun.created_at',
        uselist=False
    )

    def after_run(self) -> None:
        self.runner_type.after_run(self)

    @property
    def ipaddr(self) -> str:
        return self._ipaddr

    @property
    def runner_type(self) -> t.Type['auto_test_module.AutoTestRunner']:
        return auto_test_module.auto_test_runners[self._type]

    @classmethod
    def already_running(cls, ipaddr: str) -> bool:
        return db.session.query(
            cls.query.filter(
                cls._ipaddr == ipaddr,
                cls.after_state != AutoTestAfterRunState.called
            ).exists()
        ).scalar()

    @classmethod
    def create(
        cls,
        typ: t.Type[auto_test_module.AutoTestRunner],
        ipaddr: str,
    ) -> 'AutoTestRunner':
        _type_name = auto_test_module.auto_test_runners.find(typ, None)
        assert _type_name is not None

        return cls(
            _type=_type_name,
            _ipaddr=ipaddr,
        )


class AutoTestRun(Base, TimestampMixin, IdMixin):
    __tablename__ = 'AutoTestRun'

    if t.TYPE_CHECKING:  # pragma: no cover
        query: t.ClassVar[_MyQuery['AutoTestRun']]

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

    runner_id: t.Optional[uuid.UUID] = db.Column(
        'runner_id',
        UUIDType,
        db.ForeignKey('AutoTestRunner.id'),
        nullable=True,
        default=None,
    )

    runner: 'AutoTestRunner' = db.relationship(
        'AutoTestRunner',
        foreign_keys=runner_id,
        back_populates='run',
    )

    auto_test: 'AutoTest' = db.relationship(
        'AutoTest',
        foreign_keys=auto_test_id,
        back_populates='runs',
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

    @property
    def finished(self) -> bool:
        return self.state in {
            AutoTestRunState.done,
            AutoTestRunState.timed_out,
            AutoTestRunState.crashed,
        }

    @property
    def state(self) -> AutoTestRunState:
        return self._state

    @state.setter
    def state(self, new_state: AutoTestRunState) -> None:
        assert isinstance(new_state, AutoTestRunState)

        self._state = new_state

        if new_state == AutoTestRunState.done:
            for result in self.results:
                result.update_rubric()

        if self.finished and self.runner_id is not None:
            psef.tasks.reset_auto_test_runner(self.runner_id.hex)

    def start(
        self,
        runner_type: t.Type['auto_test_module.AutoTestRunner'],
        runner_ipaddr: str,
    ) -> None:
        assert self.started_date is None
        self.started_date = datetime.datetime.utcnow()
        max_duration = datetime.timedelta(
            minutes=psef.app.config['AUTO_TEST_MAX_TIME_TOTAL_RUN'],
        )
        now = datetime.datetime.utcnow()
        self.kill_date = now + max_duration
        self.runner = AutoTestRunner.create(runner_type, runner_ipaddr)
        db.session.add(self.runner)

        @psef.helpers.callback_after_this_request
        def start_tasks() -> None:
            psef.tasks.notify_slow_auto_test_run(
                (self.id, ), eta=now + (max_duration / 2)
            )
            psef.tasks.stop_auto_test_run((self.id, ), eta=self.kill_date)
            logger.info('Checking heartbeat', runner_id=self.runner.id)
            psef.tasks.check_heartbeat_auto_test_run((self.runner.id.hex, ))

    def get_instructions(self) -> auto_test_module.RunnerInstructions:
        return {
            'runner_id':
                str(self.runner.id),
            'run_id':
                self.id,
            'auto_test_id':
                self.auto_test_id,
            'result_ids': [r.id for r in self.results if not r.passed],
            'sets': [s.get_instructions() for s in self.auto_test.sets],
            'fixtures': [(f.name, f.id) for f in self.auto_test.fixtures],
            'setup_script':
                self.auto_test.setup_script,
            'heartbeat_interval':
                psef.app.config['AUTO_TEST_HEARTBEAT_INTERVAL'],
            'run_setup_script':
                self.auto_test.run_setup_script,
        }

    def __to_json__(self) -> t.Mapping[str, object]:
        return {
            'id': self.id,
            'created_at': self.created_at.isoformat(),
            'state': self.state.name,
        }

    def __extended_to_json__(self) -> t.Mapping[str, object]:
        results = []
        for result in self.results:
            try:
                auth.ensure_can_see_grade(result.work)
            except exceptions.PermissionException:
                continue
            else:
                results.append(result)

        # TODO: Check permissions for setup_stdout/setup_stderr
        return {
            **self.__to_json__(),
            'results': results,
            'setup_stdout': self.setup_stdout,
            'setup_stderr': self.setup_stderr,
        }

    def delete_and_clear_rubric(self) -> None:
        for result in self.results:
            result.clear_rubric()
        db.session.delete(self)


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
        query: t.ClassVar[_MyQuery['AutoTest']]
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
        cascade='all,delete',
        order_by='AutoTestSet.created_at'
    )  # type: t.MutableSequence[AutoTestSet]

    runs = db.relationship(
        "AutoTestRun",
        back_populates="auto_test",
        cascade='all,delete',
        order_by='AutoTestRun.created_at'
    )  # type: t.MutableSequence[AutoTestRun]

    fixtures = db.relationship(
        'AutoTestFixture',
        back_populates="auto_test",
        cascade='all,delete',
        order_by="AutoTestFixture.name"
    )  # type: t.MutableSequence[file_models.AutoTestFixture]

    setup_script: str = db.Column('setup_script', db.Unicode, nullable=False)
    run_setup_script: str = db.Column(
        'run_setup_script', db.Unicode, nullable=False
    )
    finalize_script: str = db.Column(
        'finalize_script', db.Unicode, nullable=False
    )

    @property
    def all_suites(self) -> t.Iterable[AutoTestSuite]:
        return itertools.chain.from_iterable(s.suites for s in self.sets)

    def __to_json__(self) -> t.Mapping[str, object]:
        runs: t.Sequence[AutoTestRun] = []

        if self.assignment.is_done or current_user.has_permission(
            CPerm.can_see_grade_before_open, self.assignment.course_id
        ):
            runs = self.runs

        return {
            'id': self.id,
            'fixtures': self.fixtures,
            'setup_script': self.setup_script,
            'run_setup_script': self.run_setup_script,
            'finalize_script': self.finalize_script,
            'sets': self.sets,
            'assignment_id': self.assignment.id,
            'runs': runs,
        }
