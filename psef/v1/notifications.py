import typing as t

from sqlalchemy.orm import defaultload
from typing_extensions import TypedDict

from cg_json import ExtendedJSONResponse

from . import api
from .. import auth, models, helpers, current_user
from ..models import Notification, db
from ..helpers import did_raise, request_arg_true
from ..exceptions import PermissionException


class NotificationsJSON(TypedDict):
    notifications: t.List[Notification]


_MAX_NOTIFICATION_AMOUNT = 100


@api.route('/notifications/')
@auth.login_required
def get_all_notifications() -> ExtendedJSONResponse[NotificationsJSON]:
    notifications = db.session.query(Notification).filter(
        Notification.receiver == current_user
    ).order_by(
        Notification.read.desc(),
        Notification.created_at.desc(),
    ).options(
        defaultload(
            Notification.comment_reply,
        ).defaultload(
            models.CommentReply.comment_base,
        ).defaultload(
            models.CommentBase.file,
        ).selectinload(
            models.File.work,
        ),
    )

    if request_arg_true('unread_only'):
        notifications.filter(~Notification.read)

    def can_see(noti: Notification) -> bool:
        return not did_raise(
            auth.NotificationPermissions(noti).ensure_may_see,
            PermissionException,
        )

    return ExtendedJSONResponse.make(
        {
            'notifications':
                [
                    n for n in notifications.limit(_MAX_NOTIFICATION_AMOUNT)
                    if can_see(n)
                ],
        },
        use_extended=(models.CommentReply, Notification)
    )


@api.route('/notifications/<int:notification_id>', methods=['PATCH'])
def update_notification(notification_id: int
                        ) -> ExtendedJSONResponse[Notification]:
    with helpers.get_from_request_transaction() as [get, _]:
        read = get('read', bool)

    notification = helpers.get_or_404(
        Notification,
        notification_id,
        also_error=lambda n: did_raise(
            auth.NotificationPermissions(n).ensure_may_see, PermissionException
        )
    )

    auth.NotificationPermissions(notification).ensure_may_edit()
    notification.read = read
    db.session.commit()

    return ExtendedJSONResponse.make(
        notification, use_extended=(models.CommentReply, Notification)
    )


@api.route('/notifications/', methods=['PATCH'])
def update_notifications() -> ExtendedJSONResponse[NotificationsJSON]:
    with helpers.get_from_request_transaction() as [get, _]:
        notifications: t.List[helpers.JSONType] = get('notifications', list)

    notifications_to_update = {}

    for noti_json in notifications:
        with helpers.get_from_map_transaction(
            helpers.ensure_json_dict(noti_json)
        ) as [get, _]:
            notification_id = get('id', int)
            read = get('read', bool)

        notifications_to_update[notification_id] = read

    found_notifications = helpers.get_in_or_error(
        Notification,
        Notification.id,
        list(notifications_to_update.keys()),
    )
    for found_notification in found_notifications:
        auth.NotificationPermissions(found_notification).ensure_may_edit()
        found_notification.read = read

    db.session.commit()

    return ExtendedJSONResponse.make(
        {'notifications': found_notifications},
        use_extended=(models.CommentReply, Notification)
    )
