import typing as t

import sqlalchemy
from typing_extensions import Literal, TypedDict

from cg_sqlalchemy_helpers import ARRAY
from cg_sqlalchemy_helpers.types import ColumnProxy
from cg_sqlalchemy_helpers.mixins import IdMixin, TimestampMixin

from . import Base, db
from . import user as u_models
from . import comment as c_models
from ..helpers import NotEqualMixin

NotificationReason = Literal['author', 'replied', 'assignee']


class BaseNotificationJSON(TypedDict):
    id: int
    read: bool
    reasons: t.Sequence[NotificationReason]


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
    reasons: ColumnProxy[t.Tuple[NotificationReason, ...]] = db.Column(
        'reasons',
        ARRAY(db.Unicode, as_tuple=True, dimensions=1),
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
    )

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Notification):
            return self.id == other.id
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.id)

    # REVIEW: This is the correct spelling right?
    email_sent = db.Column(
        'email_sent', db.Boolean, default=False, nullable=False
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
        reasons: t.Sequence[NotificationReason],
    ) -> None:
        super().__init__(
            receiver=receiver,
            comment_reply=comment_reply,
            email_sent=False,
            read=False,
            reasons=reasons,
        )

    def __to_json__(self) -> CommentNotificationJSON:
        base = self.comment_reply.comment_base
        return {
            'id': self.id,
            'created_at': self.created_at.isoformat(),
            'reasons': self.reasons,
            'type': 'comment_notification',
            'comment_reply': self.comment_reply,
            'comment_base_id': base.id,
            'work_id': base.work.id,
            'assignment_id': base.work.assignment_id,
            'read': self.read,
            'file_id': base.file_id,
        }
