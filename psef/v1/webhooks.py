"""
This module defines all API calls for using webhooks.

Creating webhooks is not done, only the handling of webhooks is done here. You
should never really call these routes as a normal user, only services like
GitHub and GitLab use these endpoints.

SPDX-License-Identifier: AGPL-3.0-only
"""
import uuid
import typing as t

import flask
import structlog

from . import api
from .. import models
from ..helpers import JSONResponse, jsonify, get_or_404
from ..exceptions import APICodes, APIException

logger = structlog.get_logger()


@api.route('/webhooks/<uuid:webhook_id>', methods=['POST'])
def process_webhook(webhook_id: uuid.UUID) -> JSONResponse[t.Dict[str, str]]:
    """Process a webhook request.

    .. :quickref: Webhook; Process a webhook request.

    :param webhook_id: The id of the webhook to process.

    The query params differ per webhook provider. Currently the only provider
    is ``git``, which supports the ``branch`` parameter. This parameter can be
    given multiple times and controls which branches will be cloned when pushed
    to.

    :returns: A response that gives some information to the end user, the exact
        content may change at any moment.
    """
    webhook = get_or_404(models.WebhookBase, webhook_id)
    try:
        webhook.handle_request(flask.request)
    except APIException as exc:
        logger.info('Handling webhook resulted in an error', exc_info=True)
        if exc.api_code == APICodes.WEBHOOK_UNKNOWN_EVENT_TYPE:
            return jsonify(
                {
                    'message': 'Unknown event received, we will ignore it',
                },
                status_code=201
            )
        elif exc.api_code == APICodes.WEBHOOK_DIFFERENT_BRANCH:
            return jsonify(
                {
                    'message':
                        (
                            'Got push to a branch that is not monitored, we'
                            ' will ignore it'
                        ),
                },
                status_code=202
            )
        raise

    return jsonify({'message': 'Request processed, will create a submission.'})
