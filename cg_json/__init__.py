import enum
import typing as t
from json import JSONEncoder

import flask
import structlog
from flask import current_app

T = t.TypeVar('T')
logger = structlog.get_logger()


class SerializableEnum(enum.Enum):
    def __to_json__(self) -> str:
        return self.name


class ExtendedJSONResponse(t.Generic[T]):
    """A datatype for a JSON response created by using the
    ``__extended_to_json__`` if available.

    This is a subtype of :py:class:`werkzeug.wrappers.Response` where the body
    is a valid JSON object and ``content-type`` is ``application/json``.

    .. warning::

        This class is only used for type hinting and is never actually used! It
        does not contain any valid data!
    """

    def __init__(self) -> None:  # pragma: no cover
        raise NotImplementedError("Do not use this class as actual data")


class JSONResponse(t.Generic[T]):
    """A datatype for a JSON response.

    This is a subtype of :py:class:`werkzeug.wrappers.Response` where the body
    is a valid JSON object and ``content-type`` is ``application/json``.

    .. warning::

        This class is only used for type hinting and is never actually used! It
        does not contain any valid data!
    """

    def __init__(self) -> None:  # pragma: no cover
        raise NotImplementedError("Do not use this class as actual data")


class CustomJSONEncoder(JSONEncoder):
    """This JSON encoder is used to enable the JSON serialization of custom
    classes.

    Classes can define their serialization by implementing a `__to_json__`
    method.
    """

    def default(self, o: t.Any) -> t.Any:  # pylint: disable=method-hidden
        """A way to serialize arbitrary methods to JSON.

        Classes can use this method by implementing a `__to_json__` method that
        should return a JSON serializable object.

        :param obj: The object that should be converted to JSON.
        """
        try:
            return o.__to_json__()
        except AttributeError:  # pragma: no cover
            return super().default(o)


def get_extended_encoder_class(
    use_extended: t.Callable[[object], bool],
) -> t.Type:
    """Get a json encoder class.

    :param use_extended: The returned class only uses the
        ``__extended_to_json__`` method if this callback returns something that
        is equal to ``True``. This method is called with a single argument that
        is the object that is currently encoded.
    :returns: A class (not a instance!) that can be used as ``JSONEncoder``
        class.
    """

    class CustomExtendedJSONEncoder(JSONEncoder):
        """This JSON encoder is used to enable the JSON serialization of custom
        classes.

        Classes can define their serialization by implementing a
        `__extended_to_json__` or a `__to_json__` method. This class first
        tries the extended method and if it does not exist it tries to normal
        one.
        """

        # These are false positives by pylint.
        def default(self, o: t.Any) -> t.Any:  # pylint: disable=method-hidden
            """A way to serialize arbitrary methods to JSON.

            Classes can use this method by implementing a `__to_json__` method
            that should return a JSON serializable object.

            :param o: The object that should be converted to JSON.
            """
            if hasattr(o, '__extended_to_json__') and use_extended(o):
                try:
                    return o.__extended_to_json__()
                except AttributeError:  # pragma: no cover
                    pass

            try:
                return o.__to_json__()
            except AttributeError:  # pragma: no cover
                return super().default(o)

    return CustomExtendedJSONEncoder


def _maybe_log_response(obj: object, response: t.Any, extended: bool) -> None:
    if not isinstance(obj, Exception):
        to_log = str(b''.join(response.response))
        max_length = 1000
        if len(to_log) > max_length:
            logger.bind(truncated=True, truncated_size=len(to_log))
            to_log = '{1:.{0}} ... [TRUNCATED]'.format(max_length, to_log)

        ext = 'extended ' if extended else ''
        logger.info(
            f'Created {ext}json return response',
            reponse_type=str(type(obj)),
            response=to_log,
        )
        logger.try_unbind('truncated', 'truncated_size')


def extended_jsonify(
    obj: T,
    status_code: int = 200,
    use_extended: t.Union[t.Callable[[object], bool],
                          type,
                          t.Tuple[type, ...],
                          ] = object,
) -> ExtendedJSONResponse[T]:
    """Create a response with the given object ``obj`` as json payload.

    This function differs from :py:func:`jsonify` by that it used the
    ``__extended_to_json__`` magic function if it is available.

    :param obj: The object that will be jsonified using
        :py:class:`~.CustomExtendedJSONEncoder`
    :param statuscode: The status code of the response
    :param use_extended: The ``__extended_to_json__`` method is only used if
        this function returns something that equals to ``True``. This method is
        called with object that is currently being encoded. You can also pass a
        class or tuple as this parameter which is converted to
        ``lambda o: isinstance(o, passed_value)``.
    :returns: The response with the jsonified object as payload
    """
    try:
        old_encoder = current_app.json_encoder
        if isinstance(use_extended, (tuple, type)):
            class_only = use_extended
            use_extended = lambda o: isinstance(o, class_only)
        current_app.json_encoder = get_extended_encoder_class(use_extended)
        response = flask.make_response(flask.jsonify(obj))
    finally:
        current_app.json_encoder = old_encoder

    response.status_code = status_code

    _maybe_log_response(obj, response, True)

    return response


def jsonify(
    obj: T,
    status_code: int = 200,
) -> JSONResponse[T]:
    """Create a response with the given object ``obj`` as json payload.

    :param obj: The object that will be jsonified using
        :py:class:`~.CustomJSONEncoder`
    :param statuscode: The status code of the response
    :returns: The response with the jsonified object as payload
    """
    try:
        old_encoder = current_app.json_encoder
        current_app.json_encoder = CustomJSONEncoder
        response = flask.jsonify(obj)
    finally:
        current_app.json_encoder = old_encoder

    response.status_code = status_code

    _maybe_log_response(obj, response, False)

    return response
