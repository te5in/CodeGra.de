"""
This module implements all errors and warnings for psef.

This module does not contain any error checking or handling.

:license: AGPLv3, see LICENSE for details.
"""
import typing as t
from enum import IntEnum, unique

import structlog
from flask import Response, g, jsonify, request

import psef

HttpWarning = t.NewType('HttpWarning', str)  # pylint: disable=invalid-name

logger = structlog.get_logger()


@unique
class APIWarnings(IntEnum):
    """API codes used to signal warnings to the client.
    """
    DEPRECATED = 0
    GRADER_NOT_DONE = 1
    CONDITION_ALREADY_MET = 2


@unique
class APICodes(IntEnum):
    """Internal API codes that are used by :class:`APIException` objects.
    """
    INCORRECT_PERMISSION = 0
    NOT_LOGGED_IN = 1
    OBJECT_ID_NOT_FOUND = 2
    OBJECT_WRONG_TYPE = 3
    MISSING_REQUIRED_PARAM = 4
    INVALID_PARAM = 5
    REQUEST_TOO_LARGE = 6
    LOGIN_FAILURE = 7
    INACTIVE_USER = 8
    INVALID_URL = 9
    OBJECT_NOT_FOUND = 10
    BLOCKED_ASSIGNMENT = 11
    INVALID_CREDENTIALS = 12
    INVALID_STATE = 13
    INVALID_OAUTH_REQUEST = 14
    DISABLED_FEATURE = 15
    UNKOWN_ERROR = 16
    INVALID_FILE_IN_ARCHIVE = 17
    NO_FILES_SUBMITTED = 18
    RATE_LIMIT_EXCEEDED = 19
    OBJECT_ALREADY_EXISTS = 20
    INVALID_ARCHIVE = 21
    ROUTE_NOT_FOUND = 22


class APIException(Exception):
    """The exception to use if an API call failed.

    :param message: The user friendly message to display.
    :param description: The description used for debugging.
    :param api_code: The error code in the API, should be a constant
                            from this class.
    :param status_code: The Http status code to use, should not be 2xx.
    :param rest: All the other fields to return in the JSON object.
    """

    def __init__(
        self, message: str, description: str, api_code: APICodes,
        status_code: int, **rest: t.Any
    ) -> None:
        super(APIException, self).__init__()
        self.status_code = status_code
        self.api_code = api_code
        self.description = description
        self.message = message
        self.rest = rest

    def __to_json__(self) -> t.Mapping[t.Any, t.Any]:
        """Creates a JSON serializable representation of this object.

        :returns: This APIException instance as a dictionary.
        """
        ret = dict(self.rest)  # type: t.MutableMapping[t.Any, t.Any]
        ret['message'] = self.message
        ret['description'] = self.description
        ret['code'] = self.api_code.name
        return ret


def make_warning(warning_text: str, code: APIWarnings) -> HttpWarning:
    """Make a ``HttpWarning`` with the given warning and code.

    :param warning_text: The text that describes the warning.
    :param code: The warning code to associate with the warning.
    :returns: A warning with the given text and code.
    """
    return HttpWarning(
        '{:03d} CodeGrad.de "{}"'.format(
            code.value,
            warning_text.replace('"', '\\"'),
        )
    )


def init_app(app: t.Any) -> None:
    """Initialize the flask app by setting an error handler.

    :param app: The app to initialize
    """

    @app.errorhandler(APIException)
    def handle_api_error(error: APIException) -> Response:  # pylint: disable=unused-variable
        """Handle an :class:`APIException` by converting it to a
        :class:`flask.Response`.

        :param APIException error: The error that occurred
        :returns: A response with the JSON serialized error as content.
        :rtype: flask.Response
        """
        response = jsonify(error)
        response.status_code = error.status_code
        logger.warning(
            'APIException occurred',
            api_exception=error.__to_json__(),
        )
        psef.models.db.session.expire_all()
        return response

    # Coverage is disabled for the next to handlers as they should never
    # run. When they run there is a bug in the application so we cant really
    # test them.

    @app.errorhandler(404)
    def handle_404(_: object) -> Response:  # pylint: disable=unused-variable; #pragma: no cover
        api_exp = APIException(
            'The request route was not found',
            f'The route "{request.path}" does not exist',
            APICodes.ROUTE_NOT_FOUND, 404
        )
        response = jsonify(api_exp)
        logger.warning('A unknown route was requested')
        response.status_code = 404
        return response

    @app.errorhandler(Exception)
    def __handle_unknown_error(_: Exception) -> Response:  # pylint: disable=unused-variable; #pragma: no cover
        """Handle an unhandled error.

        This function should never really be called, as it means our code
        contains a bug.
        """
        api_exp = APIException(
            f'Something went wrong (id: {g.request_id})', (
                'The reason for this is unknown, '
                'please contact the system administrator'
            ), APICodes.UNKOWN_ERROR, 500
        )
        response = jsonify(api_exp)
        response.status_code = 500
        logger.error('Unknown exception occurred', exc_info=True)
        psef.models.db.session.expire_all()
        return response
