"""This module defines a Snippet.

SPDX-License-Identifier: AGPL-3.0-only
"""

import typing as t

from . import Base, db, _MyQuery
from .user import User


class Snippet(Base):
    """Describes a :class:`.User` specified mapping from a keyword to some
    string.
    """
    __tablename__ = 'Snippet'
    id = db.Column('id', db.Integer, primary_key=True)
    key = db.Column('key', db.Unicode, nullable=False)
    value = db.Column('value', db.Unicode, nullable=False)
    user_id = db.Column('User_id', db.Integer, db.ForeignKey('User.id'))

    user = db.relationship(User, foreign_keys=user_id)

    @classmethod
    def get_all_snippets(cls: t.Type['Snippet'],
                         user: User) -> t.Sequence['Snippet']:
        """Return all snippets of the given :class:`.User`.

        :param user: The user to get the snippets for.
        :returns: List of all snippets of the user.
        """
        return cls.query.filter_by(user_id=user.id).order_by(cls.id).all()

    def __to_json__(self) -> t.Mapping[str, t.Any]:
        """Creates a JSON serializable representation of this object.
        """
        return {
            'key': self.key,
            'value': self.value,
            'id': self.id,
        }
