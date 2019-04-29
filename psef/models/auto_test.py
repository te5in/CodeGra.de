"""This module defines all models needed for auto tests.

SPDX-License-Identifier: AGPL-3.0-only
"""
import os
import enum
import typing as t
import numbers
import datetime

from sqlalchemy.types import JSON

import psef

from . import Base, DbColumn, db
from . import file as file_models
from . import rubric as rubric_models
from . import _MyQuery
from . import assignment as assignment_models
from .mixins import IdMixin, TimestampMixin
from ..exceptions import APICodes, APIException

if t.TYPE_CHECKING:
    from . import user as user_models


class AutoTestStepType(enum.Enum):
    io_test = enum.auto()
    run_program = enum.auto()
    custom_output = enum.auto()
    check_points = enum.auto()


class AutoTestStep(Base, TimestampMixin, IdMixin):
    if t.TYPE_CHECKING:  # pragma: no cover
        query: t.ClassVar[_MyQuery['AutoTestStep']]
    __tablename__ = 'AutoTestStep'
    id: int = db.Column('id', db.Integer, primary_key=True)

    order = db.Column('order', db.Integer, nullable=False)

    name: str = db.Column('name', db.Unicode, nullable=False)
    weight: float = db.Column('weight', db.Float, nullable=False)

    hidden: bool = db.Column('hidden', db.Boolean, nullable=False)

    auto_test_suite_id: int = db.Column(
        'auto_test_suite_id',
        db.Integer,
        db.ForeignKey('AutoTestSuite.id'),
        nullable=False
    )

    auto_test_suite: 'AutoTestSuite' = db.relationship(
        'AutoTestSuite',
        foreign_keys=auto_test_suite_id,
        back_populates='steps',
        lazy='joined',
        innerjoin=True,
    )

    test_type: AutoTestStepType = db.Column(
        'test_type',
        db.Enum(AutoTestStepType, native_enum=False),
        nullable=False,
    )

    data: 'psef.helpers.JSONType' = db.Column(
        'data', JSON, nullable=False, default={}
    )

    def update_from_json(
        self, json: t.Dict[str, 'psef.helpers.JSONType']
    ) -> None:
        self.data = json

    def __to_json__(self) -> t.Mapping[str, object]:
        return {
            'id': self.id,
            'name': self.name,
            'type': self.test_type.name,
            'weight': self.weight,
            'data': self.data,
            'hidden': self.hidden
        }


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
        "AutoTestStep",
        back_populates="auto_test_suite",
        cascade='all,delete',
        order_by='AutoTestStep.order'
    )  # type: t.MutableSequence[AutoTestStep]

    def __to_json__(self) -> t.Mapping[str, object]:
        return {
            'id': self.id,
            'steps': self.steps,
            'rubric_row': self.rubric_row,
        }


class AutoTestStepResultState(enum.Enum):
    not_started = enum.auto()
    running = enum.auto()
    passed = enum.auto()
    failed = enum.auto()


class AutoTestStepResult(Base, TimestampMixin, IdMixin):
    if t.TYPE_CHECKING:  # pragma: no cover
        query: t.ClassVar[_MyQuery['AutoTestStepResult']]

    auto_test_step_id: int = db.Column(
        'auto_test_step_id',
        db.Integer,
        db.ForeignKey('AutoTestStep.id'),
        nullable=False
    )

    auto_test_step: AutoTestStep = db.relationship(
        'AutoTestStep',
        foreign_keys=auto_test_step_id,
        lazy='joined',
        innerjoin=True,
    )

    state = db.Column(
        'state',
        db.Enum(AutoTestStepResultState),
        default=AutoTestStepResultState.not_started,
        nullable=False,
    )

    log: 'psef.helpers.JSONType' = db.Column(
        'log',
        JSON,
        nullable=True,
        default=None,
    )

    def __to_json__(self) -> t.Mapping[str, object]:
        return {
            'id': self.id,
            'auto_test_step_id': self.auto_test_step_id,
            'state': self.state,
            'log': self.log,
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

    def __to_json__(self) -> t.Mapping[str, object]:
        return {
            'id': self.id,
            'suites': self.suites,
            'stop_points': self.stop_points,
        }


class AutoTestRun(Base, TimestampMixin, IdMixin):
    if t.TYPE_CHECKING:  # pragma: no cover
        query: t.ClassVar[_MyQuery['AutoTestRun']]

    auto_test_id: int = db.Column(
        'auto_test_id',
        db.Integer,
        db.ForeignKey('AutoTest.id'),
        nullable=False
    )

    auto_test: 'AutoTest' = db.relationship(
        'AutoTest',
        foreign_keys=auto_test_id,
        back_populates='runs',
        lazy='joined',
        innerjoin=True,
    )

    user_id: int = db.Column(
        'user_id',
        db.Integer,
        db.ForeignKey('User.id', ondelete='CASCADE'),
        nullable=False,
    )
    user = db.relationship(
        'User', foreign_keys=user_id
    )  # type: user_models.User


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

    base_systems: 'psef.helpers.JSONType' = db.Column(
        'base_systems', JSON, nullable=False, default=[]
    )

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
    finalize_script: str = db.Column(
        'finalize_script', db.Unicode, nullable=False
    )

    def __to_json__(self) -> t.Mapping[str, object]:
        return {
            'id': self.id,
            'fixtures': self.fixtures,
            'setup_script': self.setup_script,
            'finalize_script': self.finalize_script,
            'sets': self.sets,
            'assignment_id': self.assignment.id,
            'base_systems': self.base_systems,
        }
