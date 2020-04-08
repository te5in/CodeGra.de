import enum
import typing as t

import sqlalchemy
from typing_extensions import Literal, TypedDict

from cg_sqlalchemy_helpers import ArrayOfEnum
from cg_sqlalchemy_helpers.types import DbEnum, ColumnProxy
from cg_sqlalchemy_helpers.mixins import IdMixin, TimestampMixin

from . import Base, db
from . import user as u_models
from . import comment as c_models
from ..helpers import NotEqualMixin


class NotificationReasons(enum.Enum):
    assignee = 1
    author = 2
    replied = 3

    def __lt__(self, other: 'NotificationReasons') -> bool:
        return self.name < other.name

    def __to_json__(self) -> str:
        return self.name


NOTIFCATION_REASON_EXPLANATION: t.Mapping[NotificationReasons, str] = {
    NotificationReasons.author: 'you are the author of the submission',
    NotificationReasons.replied: 'you replied to this comment thread',
    NotificationReasons.assignee: 'you are the assignee of this submission',
}


def NotificationReasonEnum() -> DbEnum[NotificationReasons]:
    return db.Enum(NotificationReasons, name='notification_reason')


class BaseNotificationJSON(TypedDict):
    id: int
    read: bool
    reasons: t.List[t.Tuple[NotificationReasons, str]]


class CommentNotificationJSON(BaseNotificationJSON, TypedDict):
    type: Literal['comment_notification']
    created_at: str
    comment_reply: 'c_models.CommentReply'
    comment_base_id: int
    work_id: int
    assignment_id: int
    file_id: int


class Notification(Base, IdMixin, TimestampMixin, NotEqualMixin):
    receiver_id = db.Column(
        'receiver_id',
        db.Integer,
        db.ForeignKey('User.id', ondelete='CASCADE'),
        nullable=False,
    )
    reasons = db.Column(
        'reasons',
        ArrayOfEnum(NotificationReasonEnum()),
        nullable=False,
    )

    receiver = db.relationship(
        lambda: u_models.User,
        foreign_keys=receiver_id,
        innerjoin=True,
    )

    comment_reply_id = db.Column(
        'comment_reply_id',
        db.Integer,
        db.ForeignKey('comment_reply.id'),
        nullable=False,
    )

    comment_reply = db.relationship(
        lambda: c_models.CommentReply,
        foreign_keys=comment_reply_id,
        innerjoin=True,
        back_populates='notifications',
        lazy='joined',
        uselist=False,
    )

    @property
    def deleted(self) -> bool:
        return self.comment_reply.deleted

    @property
    def reasons_with_explanation(
        self
    ) -> t.List[t.Tuple[NotificationReasons, str]]:
        return sorted(
            [(r, NOTIFCATION_REASON_EXPLANATION[r]) for r in self.reasons]
        )

    email_sent_at = db.Column(
        'email_sent_at',
        db.TIMESTAMP(timezone=True),
        default=None,
        nullable=True,
    )

    read = db.Column('read', db.Boolean, default=False, nullable=False)

    __table_args__ = (
        db.CheckConstraint(
            sqlalchemy.func.array_length(reasons, 1) > 0,
            name='notifications_addleastonereason',
        ),
    )

    def __init__(
        self,
        receiver: 'u_models.User',
        comment_reply: 'c_models.CommentReply',
        reasons: t.Sequence[NotificationReasons],
    ) -> None:
        super().__init__(
            receiver=u_models.User.resolve(receiver),
            comment_reply=comment_reply,
            email_sent_at=None,
            read=False,
            reasons=reasons,
        )

    def __to_json__(self) -> CommentNotificationJSON:
        base = self.comment_reply.comment_base
        return {
            'id': self.id,
            'created_at': self.created_at.isoformat(),
            'reasons': self.reasons_with_explanation,
            'type': 'comment_notification',
            'comment_reply': self.comment_reply,
            'comment_base_id': base.id,
            'work_id': base.work.id,
            'assignment_id': base.work.assignment_id,
            'read': self.read,
            'file_id': base.file_id,
        }

    def __structlog__(self) -> t.Mapping[str, object]:
        return {
            'type': self.__class__.__name__,
            'id': self.id,
            'reasons': self.reasons,
            'receiver': self.receiver,
        }
