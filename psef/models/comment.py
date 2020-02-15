"""This module defines a Comment.

SPDX-License-Identifier: AGPL-3.0-only
"""

import typing as t

import psef

from . import Base, db
from . import file as file_models
from . import user as user_models
from . import _MyQuery
from ..permissions import CoursePermission


class Comment(Base):
    """Describes a comment placed in a :class:`.file_models.File` by a
    :class:`.user_models.User` with the ability to grade.

    A comment is always linked to a specific line in a file.
    """
    if t.TYPE_CHECKING:  # pragma: no cover
        query: t.ClassVar[_MyQuery['Comment']] = Base.query
    __tablename__ = "Comment"
    file_id = db.Column(
        'File_id',
        db.Integer,
        db.ForeignKey('File.id', ondelete='CASCADE'),
        nullable=False,
    )
    user_id = db.Column(
        'User_id',
        db.Integer,
        db.ForeignKey('User.id', ondelete='CASCADE'),
        nullable=False,
    )
    line = db.Column('line', db.Integer, nullable=False)
    comment = db.Column('comment', db.Unicode, nullable=False)
    __table_args__ = (db.PrimaryKeyConstraint(file_id, line), )

    file = db.relationship(
        lambda: file_models.File, foreign_keys=file_id, innerjoin=True
    )
    user = db.relationship(
        lambda: user_models.User, foreign_keys=user_id, innerjoin=True
    )

    def __to_json__(self) -> t.Mapping[str, t.Any]:
        """Creates a JSON serializable representation of this object.


        This object will look like this:

        .. code:: python

            {
                'line': int, # The line of this comment.
                'msg': str,  # The message of this comment.
                'author': t.Optional[user_models.User], # The author of this
                                                        # comment. This is
                                                        # ``None`` if the user
                                                        # does not have
                                                        # permission to see it.
            }

        :returns: A object as described above.
        """
        res: t.Dict[str, t.Union[int, str, t.Optional[user_models.User]]] = {
            'line': self.line,
            'msg': self.comment,
        }

        if psef.current_user.has_permission(
            CoursePermission.can_see_assignee,
            self.file.work.assignment.course_id
        ):
            res['author'] = self.user

        return res
