import abc
import typing as t

import structlog
from flask import Blueprint, Response, abort, g, make_response, request

from cg_json import jsonify

from . import BrokerFlask

logger = structlog.get_logger()


class APIException(abc.ABC, Exception):
    MESSAGE: str

    def __init__(self, status: int) -> None:
        super().__init__()
        self.status = status


class PermissionException(APIException):
    MESSAGE = 'Not enough/no permissions/credentials'


class NotFoundException(APIException):
    MESSAGE = 'Object not found'

    def __init__(self) -> None:
        super().__init__(404)


class BadRequest(APIException):
    MESSAGE = 'Object missing or some types are wrong'

    def __init__(self) -> None:
        super().__init__(400)


def init_app(app: BrokerFlask) -> None:
    @app.errorhandler(APIException)
    def on_error(error: APIException) -> Response:
        logger.warning('APIException occurred', exc_info=True)
        res = t.cast(t.Any, jsonify({'error': error.MESSAGE}))
        res.status_code = error.status
        return res

    @app.errorhandler(Exception)
    def on_unknown_error(_: APIException) -> Response:
        logger.warning('Unknown exception occurred', exc_info=True)
        res = t.cast(
            t.Any,
            jsonify({
                'error':
                'Something unknown went wrong! (request_id: {})'.format(
                    g.request_id)
            }))
        res.status_code = 500
        return res
