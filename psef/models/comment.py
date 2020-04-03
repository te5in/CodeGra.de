"""This module defines a Comment.

SPDX-License-Identifier: AGPL-3.0-only
"""
import enum
import typing as t
import hashlib
from collections import defaultdict

import sqlalchemy
from sqlalchemy.orm import column_property
from werkzeug.utils import cached_property
from typing_extensions import Literal

import psef
from cg_dt_utils import DatetimeWithTimezone
from cg_flask_helpers import callback_after_this_request
from cg_sqlalchemy_helpers.types import ImmutableColumnProxy
from cg_sqlalchemy_helpers.mixins import IdMixin, TimestampMixin

from . import Base, db
from . import file as file_models
from . import user as user_models
from . import _MyQuery
from . import notification as n_models
from .. import current_app, current_user
from ..permissions import CoursePermission


@enum.unique
class CommentReplyType(enum.Enum):
    plain_text = enum.auto()
    markdown = enum.auto()


class CommentReply(IdMixin, TimestampMixin, Base):
    comment_base_id = db.Column(
        'comment_base_id',
        db.Integer,
        db.ForeignKey("Comment.id"),
        nullable=False
    )

    comment_base = db.relationship(
        lambda: CommentBase,
        foreign_keys=comment_base_id,
        innerjoin=True,
        back_populates='replies',
        lazy='selectin',
    )

    deleted = db.Column(
        'deleted',
        db.Boolean,
        nullable=False,
        default=False,
        server_default='f'
    )

    in_reply_to_id = db.Column(
        'in_reply_to_id',
        db.Integer,
        db.ForeignKey('comment_reply.id', ondelete='SET NULL'),
        nullable=True,
    )

    author_id = db.Column(
        'author_id',
        db.Integer,
        db.ForeignKey('User.id', ondelete='CASCADE'),
        nullable=False,
    )
    author = db.relationship(
        lambda: user_models.User,
        foreign_keys=author_id,
        innerjoin=True,
    )

    in_reply_to = db.relationship(
        lambda: CommentReply,
        foreign_keys=in_reply_to_id,
        innerjoin=False,
        uselist=False,
    )
    comment = db.Column('comment', db.Unicode, nullable=False)

    edits = db.relationship(
        lambda: CommentReplyEdit,
        back_populates='comment_reply',
        uselist=True,
        lazy='dynamic',
        order_by=lambda: CommentReplyEdit.created_at.asc(),
    )

    reply_type = db.Column(
        'reply_type',
        db.Enum(CommentReplyType),
        nullable=False,
        server_default="'plain_text'"
    )

    notifications = db.relationship(
        lambda: n_models.Notification,
        back_populates='comment_reply',
        uselist=True,
    )

    # We set this property later on
    last_edit: ImmutableColumnProxy[t.Optional[DatetimeWithTimezone]]

    @property
    def can_see_author(self) -> bool:
        return psef.auth.FeedbackReplyPermissions(
            self
        ).ensure_may_see_author.as_bool()

    @property
    def message_id(self) -> str:
        return 'message_reply_{id_hash}@{domain}'.format(
            id_hash=self.id, domain=current_app.config['EXTERNAL_DOMAIN']
        )

    @property
    def references(self) -> t.List['CommentReply']:
        if self.in_reply_to is None:
            return []
        else:  # pragma: no cover
            base = self.in_reply_to.references
            base.append(self.in_reply_to)
            return base

    def __init__(
        self,
        author: 'user_models.User',
        comment: str,
        reply_type: CommentReplyType,
        in_reply_to: t.Optional['CommentReply'],
        comment_base: 'CommentBase',
    ) -> None:
        assert author.group is None, 'Only normal users can place comments'

        super().__init__(
            deleted=False,
            author=author,
            comment=comment,
            reply_type=reply_type,
            in_reply_to_id=None if in_reply_to is None else in_reply_to.id,
            comment_base=comment_base,
        )

        work = self.comment_base.work
        user_reasons: t.Dict[user_models.User, t.Set[n_models.
                                                     NotificationReasons]]
        user_reasons = defaultdict(set)

        for reply in self.comment_base.replies:
            for user in reply.author.get_contained_users():
                user_reasons[user].add(n_models.NotificationReasons.replied)

        for work_author in work.user.get_contained_users():
            user_reasons[work_author].add(n_models.NotificationReasons.author)

        if work.assignee:
            for assignee in work.assignee.get_contained_users():
                user_reasons[assignee].add(
                    n_models.NotificationReasons.assignee
                )

        for receiver, reasons in user_reasons.items():
            if receiver != author:
                n_models.Notification(
                    receiver=receiver,
                    comment_reply=self,
                    reasons=sorted(reasons),
                )

        @callback_after_this_request
        def __after() -> None:
            psef.tasks.send_direct_notification_emails(
                [n.id for n in self.notifications]
            )

    def update(self, new_comment_text: str) -> 'CommentReplyEdit':
        edit = CommentReplyEdit(
            self, current_user, new_comment_text=new_comment_text
        )
        self.comment = new_comment_text
        return edit

    def delete(self) -> 'CommentReplyEdit':
        edit = CommentReplyEdit(self, current_user, is_deletion=True)
        self.deleted = True
        return edit

    def __repr__(self) -> str:
        return f'<CommentReply id={self.id} deleted={self.deleted}>'

    def __to_json__(self) -> t.Mapping[str, t.Union[str, int, None]]:
        last_edit = self.last_edit
        res: t.Dict[str, t.Union[str, int, None]] = {
            'id': self.id,
            'comment': self.comment,
            'author_id': None,
            'in_reply_to_id': self.in_reply_to_id,
            'last_edit': None if last_edit is None else last_edit.isoformat(),
            'created_at': self.created_at.isoformat(),
            'reply_type': self.reply_type.name,
        }

        if self.can_see_author:
            res['author_id'] = self.author_id

        return res

    def __extended_to_json__(
        self
    ) -> t.Mapping[str, t.Union[str, int, None, 'user_models.User']]:
        author = self.author if self.can_see_author else None
        return {
            **self.__to_json__(),
            'author': author,
        }


class CommentReplyEdit(IdMixin, TimestampMixin, Base):
    @t.overload
    def __init__(
        self, comment_reply: CommentReply, editor: 'user_models.User', *,
        is_deletion: Literal[True]
    ) -> None:
        ...

    @t.overload
    def __init__(
        self,
        comment_reply: CommentReply,
        editor: 'user_models.User',
        *,
        new_comment_text: str,
    ) -> None:
        ...

    def __init__(
        self,
        comment_reply: CommentReply,
        editor: 'user_models.User',
        *,
        new_comment_text: str = None,
        is_deletion: bool = False,
    ) -> None:
        ...
        assert comment_reply.id is not None, 'CommentReply should be in db'
        super().__init__(
            comment_reply_id=comment_reply.id,
            new_comment=new_comment_text,
            is_deletion=is_deletion,
            old_comment=comment_reply.comment,
            editor_id=editor.id,
        )

    comment_reply_id = db.Column(
        'comment_reply_id',
        db.Integer,
        db.ForeignKey(CommentReply.id),
        nullable=False,
    )

    comment_reply = db.relationship(
        lambda: CommentReply,
        foreign_keys=comment_reply_id,
        innerjoin=True,
        back_populates='edits',
    )

    editor_id = db.Column(
        'editor_id',
        db.Integer,
        db.ForeignKey('User.id', ondelete='CASCADE'),
        nullable=False,
    )

    new_comment = db.Column('new_comment', db.Unicode, nullable=True)
    is_deletion = db.Column('was_deleted', db.Boolean, nullable=False)
    old_comment = db.Column('old_comment', db.Unicode, nullable=False)

    __table_args__ = (
        db.CheckConstraint(
            'new_comment IS NOT NULL OR was_deleted',
            name='either_new_comment_or_deletion'
        ),
    )


CommentReply.last_edit = column_property(
    sqlalchemy.sql.select(
        [sqlalchemy.sql.func.max(CommentReplyEdit.created_at)]
    ).where(CommentReplyEdit.comment_reply_id == CommentReply.id
            ).correlate_except(CommentReplyEdit).label('last_edit')
)


class CommentBase(IdMixin, Base):
    """Describes a comment placed in a :class:`.file_models.File` by a
    :class:`.user_models.User` with the ability to grade.

    A comment is always linked to a specific line in a file.
    """
    if t.TYPE_CHECKING:  # pragma: no cover
        query: t.ClassVar[_MyQuery['CommentBase']] = Base.query
    __tablename__ = "Comment"
    file_id = db.Column(
        'File_id',
        db.Integer,
        db.ForeignKey('File.id', ondelete='CASCADE'),
        nullable=False,
    )
    line = db.Column('line', db.Integer, nullable=False)
    __table_args__ = (db.UniqueConstraint(file_id, line), )

    file = db.relationship(
        lambda: file_models.File,
        foreign_keys=file_id,
        innerjoin=True,
        lazy='selectin',
    )

    replies = db.relationship(
        lambda: CommentReply,
        back_populates='comment_base',
        uselist=True,
        lazy='selectin',
        order_by=lambda: CommentReply.created_at.asc(),
        primaryjoin=lambda: sqlalchemy.and_(
            CommentBase.id == CommentReply.comment_base_id,
            ~CommentReply.deleted,
        )
    )

    @property
    def work(self) -> 'psef.models.Work':
        return self.file.work

    @property
    def message_id(self) -> str:
        return 'message_base_{id_hash}@{domain}'.format(
            id_hash=self.id, domain=current_app.config['EXTERNAL_DOMAIN']
        )

    def add_reply(
        self,
        user: 'user_models.User',
        comment: str,
        reply_type: CommentReplyType,
        in_reply_to: t.Optional[CommentReply],
    ) -> CommentReply:
        reply = CommentReply(
            comment=comment,
            author=user,
            reply_type=reply_type,
            in_reply_to=in_reply_to,
            comment_base=self,
        )
        return reply

    @classmethod
    def create(cls, file: 'file_models.File', line: int) -> 'CommentBase':
        return cls(file=file, file_id=file.id, line=line, replies=[])

    @classmethod
    def create_if_not_exists(
        cls, file: 'file_models.File', line: int
    ) -> 'CommentBase':
        self = cls.query.filter(
            cls.file_id == file.id,
            cls.line == line,
        ).one_or_none()
        if self is None:
            self = cls.create(file, line)
        return self

    @classmethod
    def create_and_add_reply(
        cls,
        file: 'file_models.File',
        line: int,
        user: 'user_models.User',
        comment: str,
        reply_type: CommentReplyType,
    ) -> t.Tuple['CommentBase', CommentReply]:
        self = cls.create(file, line)
        reply = self.add_reply(user, comment, reply_type, None)
        return self, reply

    @property
    def first_reply(self) -> t.Optional['CommentReply']:
        return self.replies[0] if self.replies else None

    @property
    def comment(self) -> t.Optional[str]:
        fr = self.first_reply
        return fr.comment if fr else None

    @property
    def user(self) -> t.Optional['user_models.User']:
        fr = self.first_reply
        return fr.author if fr else None

    def get_outdated_json(self) -> t.Mapping[str, object]:
        first_reply = self.first_reply
        return {
            'id': self.id,
            'line': self.line,
            'file_id': self.file_id,
            'msg': self.comment,
            'author':
                self.user if
                (first_reply and first_reply.can_see_author) else None,
        }

    def __to_json__(self) -> t.Mapping[str, t.Any]:
        """Creates a JSON serializable representation of this object.


        This object will look like this:

        .. code:: python

            {
                'line': int, # The line of this comment.
                'file_id': str, # The file this feedback was given on.
                'replies': t.List[CommentReply] # All the replies on this
                                                # comment base.
            }

        :returns: A object as described above.
        """
        return {
            'id': self.id,
            'line': self.line,
            'file_id': str(self.file_id),
            'replies': self.replies,
        }
