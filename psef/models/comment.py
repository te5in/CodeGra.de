"""This module defines a Comment.

SPDX-License-Identifier: AGPL-3.0-only
"""

import enum
import typing as t

import sqlalchemy
from sqlalchemy.orm import column_property
from werkzeug.utils import cached_property
from typing_extensions import Literal

import psef
from cg_sqlalchemy_helpers.types import ImmutableColumnProxy
from cg_sqlalchemy_helpers.mixins import IdMixin, TimestampMixin

from . import Base, db
from . import file as file_models
from . import user as user_models
from . import _MyQuery
from .. import current_user
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

    # We set this property later on
    has_edits: ImmutableColumnProxy[bool]

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
        res: t.Dict[str, t.Union[str, int, None]] = {
            'id': self.id,
            'comment': self.comment,
            'author_id': None,
            'in_reply_to_id': self.in_reply_to_id,
            'has_edits': self.has_edits,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'reply_type': self.reply_type.name,
        }

        if self.comment_base.can_see_author:
            res['author_id'] = self.author_id

        return res


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


CommentReply.has_edits = column_property(
    sqlalchemy.sql.exists(
        [1]
    ).where(CommentReplyEdit.comment_reply_id == CommentReply.id
            ).correlate_except(CommentReplyEdit).label('has_edits')
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
    )

    @cached_property
    def can_see_author(self) -> bool:
        return psef.current_user.has_permission(
            CoursePermission.can_see_assignee,
            self.file.work.assignment.course_id
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

    def add_reply(
        self,
        user: 'user_models.User',
        comment: str,
        reply_type: CommentReplyType,
        in_reply_to: t.Optional[CommentReply],
    ) -> CommentReply:
        reply = CommentReply(
            deleted=False,
            comment=comment,
            author_id=user.id,
            reply_type=reply_type
        )
        self.replies.append(reply)
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

    def __to_json__(self) -> t.Mapping[str, t.Any]:
        """Creates a JSON serializable representation of this object.


        This object will look like this:

        .. code:: python

            {
                'line': int, # The line of this comment.
                'msg': str,  # The message of this comment.
                             # DEPRECATED: use the replies property.
                'author': t.Optional[user_models.User], # The author of this
                                                        # comment. This is
                                                        # ``None`` if the user
                                                        # does not have
                                                        # permission to see it.
                                                        # DEPRECATED, use the
                                                        # replies property.
                'replies': t.List[CommentReply] # All the replies on this
                                                # comment base.
            }

        :returns: A object as described above.
        """
        res: t.Dict[str, t.Union[int, str, t.Optional[user_models.User], t.
                                 List[CommentReply]]]
        print(self.replies)
        res = {
            'id': self.id,
            'line': self.line,
            'file_id': self.file_id,
            'msg': self.comment,
            'replies': self.replies,
            'author': None,
        }

        if self.can_see_author:
            res['author'] = self.user

        return res
