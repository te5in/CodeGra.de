"""
This file contains all models needed for task results.

SPDX-License-Identifier: AGPL-3.0-only
"""
import enum
import typing as t

import structlog

from cg_json import JSONResponse
from cg_sqlalchemy_helpers import JSONB
from cg_sqlalchemy_helpers.mixins import UUIDMixin, TimestampMixin

from . import Base, User, db
from ..exceptions import APICodes, APIException

logger = structlog.get_logger()


@enum.unique
class TaskResultState(enum.Enum):
    not_started = 0
    started = 1
    finished = 2
    failed = 3
    crashed = 4

    def __to_json__(self) -> str:
        return self.name


class TaskResult(Base, UUIDMixin, TimestampMixin):
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
        except Exception:
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

    def __to_json__(self) -> t.Mapping[str, object]:
        return {
            'id': str(self.id),
            'state': self.state,
            'result': self.result,
        }

    __structlog__ = __to_json__
