import abc
import enum
import typing as t
import dataclasses

from typing_extensions import Literal, TypedDict, get_type_hints
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.dialects.postgresql import JSONB

from cg_sqlalchemy_helpers import ARRAY
from cg_sqlalchemy_helpers.types import ColumnProxy
from cg_sqlalchemy_helpers.mixins import IdMixin, TimestampMixin

from . import Base, User, db
from .notification import NotificationReasonEnum


class SettingBase(TimestampMixin, IdMixin):
    @classmethod
    @abc.abstractmethod
    def get_setting_name(self) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def __to_json__(self) -> str:
        raise NotImplementedError

    if t.TYPE_CHECKING:
        user_id: ColumnProxy[int]
        user: ColumnProxy[User]
    else:

        @declared_attr
        def user_id(cls):
            return db.Column(
                'user_id',
                db.Integer,
                db.ForeignKey('User.id', ondelete='CASCADE'),
                nullable=False,
            )

        @declared_attr
        def user(cls):
            return db.relationship(
                User,
                foreign_keys=cls.user_id,
                innerjoin=True,
            )


_NotificationSettingValue = Literal['off', 'direct', 'daily', 'weekly']
# We cannot use `typing.get_args` as we need to support python 3.7
POSSIBLE_NOTIFICATION_VALUES: t.Set[_NotificationSettingValue] = set(
    _NotificationSettingValue.__args__  # type: ignore[misc]
)


class NotificationsSetting(Base, SettingBase):
    @classmethod
    def get_setting_name(self) -> str:
        return 'notification_setting'

    reason = db.Column(
        'reason',
        NotificationReasonEnum(),
        nullable=False,
    )
    value = db.Column(
        'value',
        db.Enum(
            *sorted(POSSIBLE_NOTIFICATION_VALUES),
            name='notification_setting_value'
        ),
        nullable=False,
    )

    __table_args__ = (db.UniqueConstraint(
        SettingBase.user_id,
        reason,
    ), )
