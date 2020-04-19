"""This module defines all exceptions used by the CodeGrade broker.

SPDX-License-Identifier: AGPL-3.0-only
"""
import abc
import typing as t

import flask
import structlog
from flask import g

from cg_json import JSONResponse, jsonify

from . import BrokerFlask

logger = structlog.get_logger()


class APIException(abc.ABC, Exception):
    """The generic exception that gets raised when an API request fails.
    """
    MESSAGE: str

    def __init__(self, status: int) -> None:
        super().__init__()
        self.status = status


class PermissionException(APIException):
    MESSAGE = 'Not enough/no permissions/credentials'


class NotFoundException(APIException):
    """This exception gets raised when a requested option is not found.
    """
    MESSAGE = 'Object not found'

    def __init__(self) -> None:
        super().__init__(404)


class BadRequest(APIException):
    """This exception gets raised when the request is missing keys.
    """
    MESSAGE = 'Object missing or some types are wrong'

    def __init__(self) -> None:
        super().__init__(400)


def init_app(app: BrokerFlask) -> None:
    """Initialize the given app.

    :param app: The app to initialize.
    """

    @app.errorhandler(APIException)
    def __on_error(error: APIException) -> JSONResponse[t.Dict[str, str]]:
        logger.warning('APIException occurred', exc_info=True)
        return jsonify({'error': error.MESSAGE}, status_code=error.status)

    @app.errorhandler(404)
    def __handle_404(_: object) -> str:  # pragma: no cover
        return flask.render_template('404.j2')

    @app.errorhandler(Exception)
    def __on_unknown_error(_: Exception) -> JSONResponse[t.Dict[str, str]]:
        logger.error(
            'Unknown exception occurred',
            exc_info=True,
            report_to_sentry=True,
        )
        return jsonify(
            {
                'error':
                    'Something unknown went wrong! (request_id: {})'.format(
                        g.request_id
                    )
            },
            status_code=500,
        )
