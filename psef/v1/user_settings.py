import typing as t

from flask import request

from cg_json import JSONResponse
from cg_flask_helpers import EmptyResponse

from . import api
from .. import auth, models, current_user
from ..helpers import get_from_request_transaction


def _get_user() -> 'models.User':
    token = request.args.get('token', None)
    if token is not None:
        return models.NotificationsSetting.verify_settings_change_token(token)
    else:
        auth.ensure_logged_in()
        return current_user


@api.route('/settings/notification_settings/', methods=['GET'])
def get_notification_settings(
) -> JSONResponse[models.NotificationSettingJSON]:
    user = _get_user()

    return JSONResponse.make(
        models.NotificationsSetting.get_notification_setting_json_for_user(
            user,
        )
    )


@api.route('/settings/notification_settings/', methods=['PATCH'])
def update_notification_settings() -> EmptyResponse:
    user = _get_user()

    with get_from_request_transaction() as [get, _]:
        reason = get('reason', models.NotificationReasons)
        value = get('value', models.EmailNotificationTypes)

    models.NotificationsSetting.update_for_user(
        user=user, reason=reason, value=value
    )
    models.db.session.commit()

    return EmptyResponse.make()
