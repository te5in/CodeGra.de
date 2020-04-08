import abc
import enum
import typing as t
import itertools
import dataclasses

import structlog
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from typing_extensions import Literal, TypedDict, get_type_hints
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.dialects.postgresql import JSONB

import psef
from cg_sqlalchemy_helpers import ARRAY
from cg_sqlalchemy_helpers.types import ColumnProxy
from cg_sqlalchemy_helpers.mixins import IdMixin, TimestampMixin

from . import Base, User, db
from ..auth import APICodes, PermissionException, NotificationPermissions
from .notification import (
    NOTIFCATION_REASON_EXPLANATION, Notification, NotificationReasons,
    NotificationReasonEnum
)

logger = structlog.get_logger()


class SettingBase(TimestampMixin, IdMixin):
    @classmethod
    @abc.abstractmethod
    def get_setting_name(self) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def __to_json__(self) -> str:
        raise NotImplementedError

    @classmethod
    def get_salt(cls) -> str:
        return f'setting:{cls.get_setting_name()}'

    @classmethod
    def get_settings_change_token(cls, user: User) -> str:
        return URLSafeTimedSerializer(
            psef.current_app.config['SECRET_KEY'],
            salt=cls.get_salt(),
        ).dumps(user.id)

    @classmethod
    def verify_settings_change_token(cls, token: str) -> User:
        try:
            user_id: int = URLSafeTimedSerializer(
                psef.current_app.config['SECRET_KEY'],
                salt=cls.get_salt(),
            ).loads(
                token,
                max_age=round(psef.current_app.config['SETTING_TOKEN_TIME']),
            )
        except SignatureExpired:
            logger.warning(
                'Expired signature encountered', token=token, exc_info=True
            )
            raise PermissionException(
                (
                    'The given token has expired, this probably means the'
                    ' email from which you clicked on the unsubscribe link was'
                    ' a couple of days old.'
                ), f'The given token {token} is not valid.',
                APICodes.INVALID_CREDENTIALS, 403
            )
        except BadSignature:
            logger.warning(
                'Invalid setting change token encountered',
                token=token,
                exc_info=True,
            )
            raise PermissionException(
                'The given token is not valid',
                f'The given token {token} is not valid.',
                APICodes.INVALID_CREDENTIALS, 403
            )

        return psef.helpers.get_or_404(User, user_id)

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


class EmailNotificationTypes(enum.Enum):
    direct = 1
    daily = 2
    weekly = 3
    off = 4

    @classmethod
    def ordered_options(cls) -> t.List['EmailNotificationTypes']:
        return sorted(cls.__members__.values())

    def previous_option(self) -> t.Optional['EmailNotificationTypes']:
        """Get the previous value.

        >>> EmailNotificationTypes.off.previous_option()
        <EmailNotificationTypes.weekly: 3>
        >>> EmailNotificationTypes.weekly.previous_option()
        <EmailNotificationTypes.daily: 2>
        >>> EmailNotificationTypes.daily.previous_option()
        <EmailNotificationTypes.direct: 1>
        >>> EmailNotificationTypes.direct.previous_option() is None
        True
        """
        opts = self.ordered_options()
        idx = opts.index(self)
        if idx > 0:
            return opts[idx - 1]
        return None

    def __lt__(self, other: 'EmailNotificationTypes') -> bool:
        return self.value < other.value

    def __to_json__(self) -> str:
        return self.name


class NotificationSettingOptionJSON(TypedDict):
    reason: NotificationReasons
    explanation: str
    value: EmailNotificationTypes


class NotificationSettingJSON(TypedDict):
    options: t.List[NotificationSettingOptionJSON]
    possible_values: t.List[EmailNotificationTypes]


class NotificationsSetting(Base, SettingBase):
    @classmethod
    def get_setting_name(self) -> str:
        return 'notification_settings'

    @classmethod
    def get_notification_setting_json_for_user(
        cls, user: User
    ) -> NotificationSettingJSON:
        settings = cls.get_default_values()
        settings.update(
            db.session.query(cls.reason, cls.value).filter(cls.user == user)
        )

        return {
            'options':
                [
                    {
                        'reason': reason,
                        'explanation': explanation,
                        'value': settings[reason],
                    } for reason, explanation in
                    sorted(NOTIFCATION_REASON_EXPLANATION.items())
                ],
            'possible_values': sorted(EmailNotificationTypes),
        }

    reason = db.Column(
        'reason',
        NotificationReasonEnum(),
        nullable=False,
    )
    value = db.Column(
        'value',
        db.Enum(EmailNotificationTypes, name='notification_setting_value'),
        nullable=False,
    )

    __table_args__ = (db.UniqueConstraint(
        'user_id',
        reason,
    ), )

    @staticmethod
    def get_default_values(
    ) -> t.MutableMapping[NotificationReasons, EmailNotificationTypes]:
        return {
            NotificationReasons.author: EmailNotificationTypes.direct,
            NotificationReasons.replied: EmailNotificationTypes.direct,
            NotificationReasons.assignee: EmailNotificationTypes.off,
        }

    @classmethod
    def update_for_user(
        cls, user: User, reason: NotificationReasons,
        value: EmailNotificationTypes
    ) -> None:
        # XXX: It would be useful to use an upsert here, but you cannot use
        # upserts with the orm
        pref = db.session.query(cls).filter(
            cls.user == user, cls.reason == reason
        ).with_for_update().one_or_none()
        if pref is None:
            pref = cls(user=user, reason=reason, value=value)
            db.session.add(pref)
        else:
            pref.value = value

    @classmethod
    def get_should_send_for_users(
        cls, user_ids: t.List[int]
    ) -> t.Callable[[Notification, EmailNotificationTypes], bool]:
        query = db.session.query(cls).filter(cls.user_id.in_(user_ids)
                                             ).order_by(cls.reason)

        lookup = {
            reason: {pref.user_id: pref
                     for pref in prefs}
            for reason, prefs in itertools.groupby(
                query,
                lambda noti: noti.reason,
            )
        }
        default_values = cls.get_default_values()

        def _should_send(
            notification: Notification,
            send_type: EmailNotificationTypes,
        ) -> bool:
            if send_type == EmailNotificationTypes.off:
                logger.info('Should not send notification for off type')
                return False

            previous_val = send_type.previous_option()
            if (
                previous_val is not None and
                _should_send(notification, previous_val)
            ):
                logger.info('More specific preference known')
                return False

            default_return = False
            for reason in notification.reasons:
                pref = lookup.get(reason, {}).get(notification.receiver_id)
                if pref is None:
                    default_return |= default_values[reason] == send_type
                elif pref.value == send_type:
                    return True

            return default_return

        def should_send(
            notification: Notification,
            send_type: EmailNotificationTypes,
        ) -> bool:
            if notification.deleted:
                logger.info('Notification is deleted')
                return False
            elif not NotificationPermissions(notification).set_user(
                notification.receiver
            ).ensure_may_see.as_bool():
                logger.info('No permission to see the notification')
                return False
            return _should_send(notification, send_type)

        return should_send
