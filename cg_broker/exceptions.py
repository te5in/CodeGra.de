"""This module defines all exceptions used by the CodeGrade broker.

SPDX-License-Identifier: AGPL-3.0-only
"""
import abc
import typing as t

import structlog
from flask import Response, g

from cg_json import jsonify

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
    def __on_error(error: APIException) -> Response:
        logger.warning('APIException occurred', exc_info=True)
        res = t.cast(t.Any, jsonify({'error': error.MESSAGE}))
        res.status_code = error.status
        return res

    @app.errorhandler(Exception)
    def __on_unknown_error(_: APIException) -> Response:
        logger.warning('Unknown exception occurred', exc_info=True)
        res = t.cast(
            t.Any,
            jsonify({
                'error':
                    'Something unknown went wrong! (request_id: {})'.format(
                        g.request_id
                    )
            })
        )
        res.status_code = 500
        return res
