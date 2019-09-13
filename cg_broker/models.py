"""This file defines all database models and enums used by the broker.

SPDX-License-Identifier: AGPL-3.0-only
"""
import enum
import time
import typing as t
import secrets
from datetime import datetime, timedelta

import boto3
import structlog
import transip.service
from suds import WebFault
from sqlalchemy.types import JSON

import cg_broker
import cg_sqlalchemy_helpers as cgs
from cg_logger import bound_to_logger
from cg_timers import timed_code
from cg_flask_helpers import callback_after_this_request
from cg_sqlalchemy_helpers import types, mixins

from . import BrokerFlask, app

if t.TYPE_CHECKING:
    hybrid_property = property  # pylint: disable=invalid-name
else:
    from sqlalchemy.ext.hybrid import hybrid_property

logger = structlog.get_logger()

db: cgs.types.MyDb = cgs.make_db()


def init_app(flask_app: BrokerFlask) -> None:
    cgs.init_app(db, flask_app)


if t.TYPE_CHECKING:  # pragma: no cover
    from cg_sqlalchemy_helpers.types import Base
else:
    Base: cgs.types.Base = db.Model  # pylint: disable=invalid-name

_T = t.TypeVar('_T', bound='Base')

_Y = t.TypeVar('_Y', bound='Runner')


@enum.unique
class RunnerState(enum.IntEnum):
    """This enum the possible states a runner can be in.

    A runner should never decrease its state.
    """
    not_running = 1
    creating = 2
    started = 3
    running = 4
    cleaning = 5
    cleaned = 6

    @classmethod
    def get_before_started_states(cls) -> t.List['RunnerState']:
        """Get the states in which a is runner before it posted to the alive
            route.
        """
        return [cls.not_running, cls.creating]

    @classmethod
    def get_before_running_states(cls) -> t.List['RunnerState']:
        """Get the states in which a is runner before it has ever done any
            work.

        This states are considered "safe", i.e. we can still make it switch
        jobs.
        """
        return [*cls.get_before_started_states(), cls.started]

    @classmethod
    def get_active_states(cls) -> t.List['RunnerState']:
        """Get the states in which a runner is considered active.
        """
        return [*cls.get_before_running_states(), cls.running]


@enum.unique
class RunnerType(enum.Enum):
    """This enum defines all possible platforms available for runners.

    The platform used is defined in the configuration file.
    """
    aws = enum.auto()
    transip = enum.auto()
    dev_runner = enum.auto()


class Runner(Base, mixins.TimestampMixin, mixins.UUIDMixin):
    """This class represents a abstract runner.

    A runner is used one time to execute a job.
    """
    if t.TYPE_CHECKING:  # pragma: no cover
        __mapper__: t.ClassVar[cgs.types.Mapper['Runner']]
        query: t.ClassVar[types.MyQuery['Runner']]

    __tablename__ = 'runner'

    ipaddr: str = db.Column(
        'ipaddr', db.Unicode, nullable=True, default=None, index=True
    )
    _runner_type = db.Column('type', db.Enum(RunnerType), nullable=False)
    state = db.Column(
        'state',
        db.Enum(RunnerState),
        nullable=False,
        default=RunnerState.not_running
    )
    started_at: t.Optional[datetime] = db.Column(
        db.DateTime, default=None, nullable=True
    )

    # The id used by the provider of this execution unit
    instance_id = db.Column('instance_id', db.Unicode, nullable=True)
    last_log_emitted = db.Column(
        'last_log_emitted', db.Boolean, nullable=False, default=False
    )

    job_id: t.Optional[int] = db.Column(
        'job_id',
        db.Integer,
        db.ForeignKey('job.id'),
        nullable=True,
        default=None,
        unique=False
    )

    job: t.Optional['Job'] = db.relationship(
        'Job', foreign_keys=job_id, back_populates='runners'
    )

    def cleanup_runner(self, shutdown_only: bool) -> None:
        raise NotImplementedError

    def start_runner(self) -> None:
        raise NotImplementedError

    def is_ip_valid(self, requesting_ip: str) -> bool:
        return secrets.compare_digest(self.ipaddr, requesting_ip)

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Runner):
            return self.id == other.id
        return NotImplemented

    def __ne__(self, other: object) -> bool:
        return not self == other

    @property
    def is_before_run(self) -> bool:
        """Is this runner in a state before it started executing any code.
        """
        return self.state in RunnerState.get_before_running_states()

    @property
    def should_clean(self) -> bool:
        """Is this runner in a state where it still needs cleaning.

        This is always true if the runner is not cleaned or currently being
        cleaned.
        """
        return self.state not in {RunnerState.cleaned, RunnerState.cleaning}

    @classmethod
    def get_amount_of_startable_runners(cls) -> int:
        """Get the amount of runners that can still be started.
        """
        active = len(cls.get_all_active_runners().with_for_update().all())
        max_amount = app.config['MAX_AMOUNT_OF_RUNNERS']
        return max(max_amount - active, 0)

    @classmethod
    def can_start_more_runners(cls) -> bool:
        """Is it currently allowed to start more runners.

        This checks the amount of runners currently active and makes sure this
        is less than the maximum amount of runners.
        """
        # We do a all and len here as count() and with_for_update cannot be
        # used in combination.
        amount = len(cls.get_all_active_runners().with_for_update().all())

        max_amount = app.config['MAX_AMOUNT_OF_RUNNERS']
        can_start = amount < max_amount
        logger.info(
            'Checking if we can start more runners',
            running_runners=amount,
            maximum_amount=max_amount,
            can_start_more=can_start
        )
        if not can_start:
            logger.warning('Too many runners active', active_amount=amount)
        return can_start

    @classmethod
    def _create(cls: t.Type[_Y]) -> _Y:
        return cls()

    @classmethod
    def create_of_type(cls, typ: RunnerType) -> 'Runner':
        """Create a runner of the given type.

        :param typ: The type of runner you want to create.
        :returns: The newly created runner.
        """
        return cls.__mapper__.polymorphic_map[typ].class_._create()  # pylint: disable=protected-access

    @classmethod
    def get_all_active_runners(cls) -> types.MyQuery['Runner']:
        """Get a query to get all the currently active runners.

        .. warning::

            This query does not lock these runners so do so yourself if that is
            needed.
        """
        return db.session.query(cls).filter(
            t.cast(types.DbColumn[RunnerState],
                   cls.state).in_(RunnerState.get_active_states())
        )

    def make_unassigned(self) -> None:
        """Make this runner unassigned.

        .. note::

            This also starts a job to kill this runner after a certain amount
            of time if it is still unassigned.
        """
        self.job_id = None
        eta = datetime.utcnow() + timedelta(
            minutes=app.config['RUNNER_MAX_TIME_ALIVE']
        )
        runner_hex_id = self.id.hex

        callback_after_this_request(
            lambda: cg_broker.tasks.maybe_kill_unneeded_runner.apply_async(
                (runner_hex_id, ),
                eta=eta,
            )
        )

    def kill(self, *, maybe_start_new: bool, shutdown_only: bool) -> None:
        """Kill this runner and maybe start a new one.

        :param maybe_start_new: Should we maybe start a new runner after
            killing this one.
        """
        self.state = RunnerState.cleaning
        db.session.commit()
        self.cleanup_runner(shutdown_only)
        self.state = RunnerState.cleaned
        db.session.commit()

        if maybe_start_new:
            cg_broker.tasks.maybe_start_unassigned_runner.delay()

    def __structlog__(self) -> t.Dict[str, t.Union[str, int, None]]:
        return {
            'type': str(type(self)),
            'id': self.id.hex,
            'state': self.state.name,
            'job_id': self.job_id,
            'ipaddr': self.ipaddr,
        }

    __mapper_args__ = {
        'polymorphic_on': _runner_type,
        'polymorphic_identity': None,
    }


class DevRunner(Runner):
    """This class represents a local runner, which provides zero additional
    sandboxing.

    .. danger:: Never use this runner during production.
    """
    __mapper_args__ = {
        'polymorphic_identity': RunnerType.dev_runner,
    }

    @classmethod
    def _create(cls: t.Type[_Y]) -> _Y:
        return cls(ipaddr='127.0.0.1')

    def start_runner(self) -> None:
        pass

    def cleanup_runner(self, shutdown_only: bool) -> None:
        pass


class TransipRunner(Runner):
    """This is a runner which runs using transip virtual machines.

    It is interesting to note that these machines are never terminated, their
    snapshots are simply restored.
    """

    def start_runner(self) -> None:
        pass

    def cleanup_runner(self, shutdown_only: bool) -> None:
        username = app.config['_TRANSIP_USERNAME']
        key_file = app.config['_TRANSIP_PRIVATE_KEY_FILE']
        vps_service = transip.service.VpsService(
            username, private_key_file=key_file
        )
        vps, = [
            vps for vps in vps_service.get_vpses()
            if vps['ipAddress'] == self.ipaddr
        ]
        assert vps['name'] == self.instance_id

        with bound_to_logger(vps=vps):
            vps_name = vps['name']
            snapshots = vps_service.get_snapshots_by_vps(vps_name)
            snapshot = min(snapshots, key=lambda s: s['dateTimeCreate'])
            self._retry_vps_action(
                'stopping vps', lambda: vps_service.stop(vps_name)
            )
            self._retry_vps_action(
                'reverting snapshot',
                lambda: vps_service.
                revert_snapshot(vps_name, snapshot['name']),
            )

    @staticmethod
    def _retry_vps_action(
        action_name: str, func: t.Callable[[], object], max_tries: int = 50
    ) -> None:
        with bound_to_logger(
            action=action_name,
        ), timed_code('_retry_vps_action'):
            for idx in range(max_tries):
                try:
                    func()
                except WebFault:
                    logger.info('Could not perform action yet', exc_info=True)
                    time.sleep(idx)
                else:
                    break
            else:
                logger.error("Couldn't perform action")
                raise TimeoutError

    __mapper_args__ = {'polymorphic_identity': RunnerType.transip}


class AWSRunner(Runner):
    """This class represents a runner which is running on the AWS platform.
    """

    def start_runner(self) -> None:
        assert self.instance_id is None

        client = boto3.client('ec2')
        ec2 = boto3.resource('ec2')

        images = client.describe_images(
            Owners=['self'],
            Filters=[{
                'Name': 'tag:AutoTest',
                'Values': [app.config['AWS_TAG_VALUE']]
            }],
        ).get('Images', [])
        assert images
        image = max(images, key=lambda image: image['CreationDate'])

        logger.info(
            'Creating AWS instance',
            instance_type=app.config['AWS_INSTANCE_TYPE'],
            image_id=image['ImageId']
        )

        inst, = ec2.create_instances(
            ImageId=image['ImageId'],
            InstanceType=app.config['AWS_INSTANCE_TYPE'],
            MaxCount=1,
            MinCount=1
        )

        with bound_to_logger(instance=inst):
            logger.info('Started AWS instance, waiting for network')

            self.instance_id = inst.id

            for _ in range(120):
                inst = ec2.Instance(inst.id)
                if inst.public_ip_address:
                    logger.info('AWS instance up')
                    self.ipaddr = inst.public_ip_address
                    return
                time.sleep(1)

            logger.error('Timed out waiting on AWS instance')
            raise TimeoutError

    def cleanup_runner(self, shutdown_only: bool) -> None:
        assert self.instance_id
        client = boto3.client('ec2')
        if shutdown_only:
            client.stop_instances(
                InstanceIds=[self.instance_id], Hibernate=False
            )
        else:
            client.terminate_instances(InstanceIds=[self.instance_id])

    __mapper_args__ = {'polymorphic_identity': RunnerType.aws}


@enum.unique
class JobState(enum.IntEnum):
    """This enum represents the current state of the Job.

    A job can never decrease its state, so when it is finished it can never be
    started again.
    """
    waiting_for_runner = 1
    started = 2
    finished = 3

    @property
    def is_finished(self) -> bool:
        """Is this a finished state.
        """
        return self == self.finished

    @property
    def is_waiting_for_runner(self) -> bool:
        """Is this waiting for a runner
        """
        return self == self.waiting_for_runner

    @classmethod
    def get_finished_states(cls) -> t.Sequence['JobState']:
        """Get the states that are considered finished.
        """
        return [cls.finished]


class Job(Base, mixins.TimestampMixin, mixins.IdMixin):
    """This class represents a single job.

    A job is something a CodeGrade instance needs a runner for. These jobs are
    never deleted, but its state changes during its life.
    """
    if t.TYPE_CHECKING:  # pragma: no cover
        query: t.ClassVar[types.MyQuery['Job']]

    __tablename__ = 'job'

    _state = db.Column(
        'state',
        db.Enum(JobState),
        nullable=False,
        default=JobState.waiting_for_runner
    )

    cg_url = db.Column('cg_url', db.Unicode, nullable=False)

    # It is important that this is really unique!
    remote_id = db.Column(
        'remote_id', db.Unicode, nullable=False, index=True, unique=True
    )
    runners: t.List['Runner'] = db.relationship(
        'Runner', back_populates='job', uselist=True
    )

    _job_metadata: t.Optional[t.Dict[str, object]] = db.Column(
        'job_metadata', JSON, nullable=True, default={}
    )

    @property
    def job_metadata(self) -> t.Dict[str, object]:
        """Metadata connected to this job.
        """
        return self._job_metadata or {}

    def update_metadata(self, new_values: t.Dict[str, object]) -> None:
        self._job_metadata = {**self.job_metadata, **new_values}

    _wanted_runners: int = db.Column(
        'wanted_runners',
        db.Integer,
        default=1,
        server_default='1',
        nullable=False
    )

    @property
    def wanted_runners(self) -> int:
        """The amount of runners this job wants.
        """
        return self._wanted_runners

    @wanted_runners.setter
    def wanted_runners(self, new_value: int) -> None:
        self._wanted_runners = min(
            max(new_value, 1),
            app.config['MAX_AMOUNT_OF_RUNNERS_PER_JOB'],
        )

    @hybrid_property
    def state(self) -> JobState:
        """Get the state of this job.
        """
        return self._state

    @state.setter
    def state(self, new_state: JobState) -> None:
        if self.state is not None and new_state < self.state:
            raise ValueError(
                'Cannot decrease the state!', self.state, new_state
            )
        self._state = new_state

    def get_active_runners(self) -> t.List[Runner]:
        return [
            r for r in self.runners
            if r.state in RunnerState.get_active_states()
        ]

    def __log__(self) -> t.Dict[str, object]:
        return {
            'state': self.state.name,
            'cg_url': self.cg_url,
            'id': self.id,
        }

    def __to_json__(self) -> t.Dict[str, object]:
        return {
            'id': self.remote_id,
            'state': self.state.name,
            'wanted_runners': self.wanted_runners,
        }
