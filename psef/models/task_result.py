"""
This file contains all models needed for task results.

SPDX-License-Identifier: AGPL-3.0-only
"""
import enum
import typing as t

import structlog
from typing_extensions import TypedDict

from cg_json import JSONResponse
from cg_sqlalchemy_helpers import JSONB
from cg_sqlalchemy_helpers.mixins import UUIDMixin, TimestampMixin

from . import Base, User, db
from ..exceptions import APICodes, APIException

logger = structlog.get_logger()


@enum.unique
class TaskResultState(enum.Enum):
    """The state of a task result.

    :ivar not_started: The task has not been started yet.
    :ivar started: The task has started but has not finished.
    :ivar finished: The task finished successfully.
    :ivar failed: The task failed in a way we know this task can fail.
    :ivar crashed: The task crashed, i.e. it failed in an unexpected way.
    """
    not_started = 0
    started = 1
    finished = 2
    failed = 3
    crashed = 4

    def __to_json__(self) -> str:
        return self.name


class TaskResultJSON(TypedDict):
    """The serialization scheme for a :class:`.TaskResult`.
    """
    id: str
    state: TaskResultState
    result: t.Optional[t.Mapping[str, object]]


class TaskResult(Base, UUIDMixin, TimestampMixin):
    """This class represents the state and result of a celery task.

    :ivar result: The result the task produced, or more importantly the
        exception that was raised during the task.
    :ivar ~TaskResult.user: The user that initiated the task.
    """
    state = db.Column(
        'state',
        db.Enum(TaskResultState),
        nullable=False,
        default=TaskResultState.not_started
    )
    result = db.Column('result', JSONB, nullable=True, default=None)

    user_id = db.Column(
        'author_id',
        db.Integer,
        db.ForeignKey('User.id', ondelete='CASCADE'),
        nullable=False,
    )
    user = db.relationship(User, foreign_keys=user_id, innerjoin=True)

    def __init__(self, user: User) -> None:
        super().__init__(user=User.resolve(user))

    def as_task(self, fun: t.Callable[[], None]) -> None:
        """Run the given ``fun`` as the task.

        .. warning::

            One of the first things this function do is committing the current
            session, however after running ``fun`` nothing is committed.

        :param fun: The function to run as the task, catching the exceptions it
            produces and storing them in this task result.
        :returns: Nothing.
        """
        assert self.state == TaskResultState.not_started, (
            'Cannot start task that has already started, state was in {}'
        ).format(self.state)

        self.state = TaskResultState.started
        db.session.commit()

        try:
            self.result = fun()
        except APIException as exc:
            self.state = TaskResultState.failed
            self.result = JSONResponse.dump_to_object(exc)
        except:  # pylint: disable=bare-except
            logger.warning('The task crashed', exc_info=True)
            self.state = TaskResultState.crashed
            self.result = JSONResponse.dump_to_object(
                APIException(
                    'The task failed for an unknown reason',
                    f'The task {self.id} failed with a uncaught exception',
                    APICodes.UNKOWN_ERROR, 400
                )
            )
        else:
            self.state = TaskResultState.finished

    def __to_json__(self) -> TaskResultJSON:
        """Convert this task result to json.

        :returns: A serialized task result.
        """
        return {
            'id': str(self.id),
            'state': self.state,
            'result': self.result,
        }

    __structlog__ = __to_json__
