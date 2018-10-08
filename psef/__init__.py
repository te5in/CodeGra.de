"""
This package implements the backend for codegrade. Because of historic reasons
this backend is named ``psef``.

:license: AGPLv3, see LICENSE for details.
"""
import os
import sys
import json as system_json
import uuid
import types
import typing as t
import logging
import datetime

import flask  # pylint: disable=unused-import
import structlog
import flask_jwt_extended as flask_jwt
from flask import Flask, g, jsonify, request, current_app
from sqlalchemy import event
from flask_limiter import Limiter, RateLimitExceeded
from sqlalchemy.engine.base import Engine

logger = structlog.get_logger()

app = current_app  # pylint: disable=invalid-name

LTI_ROLE_LOOKUPS = {
}  # type: t.Mapping[str, t.Mapping[str, t.Union[str, bool]]]
"""A LTI role to psef role lookup dictionary.

.. note::
    The roles are both course and user roles.
"""


def _seed_lti_lookups() -> None:
    """Seed the lti lookups.

    This is done by reading the ``lti_lookups.json`` file and setting its
    result in ``LTI_ROLE_LOOKUPS``. You should not call this function from
    application code, this code is only for the first initialization.
    """
    # Global is necessary here as we cannot set the variable otherwise
    global LTI_ROLE_LOOKUPS  # pylint: disable=global-statement
    _seed_data_path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), '..', 'seed_data',
        'lti_lookups.json'
    )
    with open(_seed_data_path, 'r') as f:
        # We freeze this map as changing it is probably never correct.
        LTI_ROLE_LOOKUPS = types.MappingProxyType(system_json.load(f))


_seed_lti_lookups()

if t.TYPE_CHECKING:  # pragma: no cover
    import psef.models  # pylint: disable=unused-import
    current_user: 'psef.models.User' = t.cast('psef.models.User', None)
else:
    current_user = flask_jwt.current_user  # pylint: disable=invalid-name


def limiter_key_func() -> None:  # pragma: no cover
    """This is the default key function for the limiter.

    The key function should be set locally at every place the limiter is used
    so this function always raises a :py:exc:`ValueError`.
    """
    raise ValueError('Key function should be overridden')


limiter = Limiter(key_func=limiter_key_func)  # pylint: disable=invalid-name


def create_app(config: t.Mapping = None, skip_celery: bool = False) -> t.Any:  # pylint: disable=too-many-statements
    """Create a new psef app.

    :param config: The config mapping that can be used to override config.
    :param skip_celery: Set to true to disable sanity checks for celery.
    :returns: A new psef app object.
    """
    import config as global_config
    resulting_app = Flask(__name__)

    @resulting_app.before_request
    def __set_request_start_time() -> None:  # pylint: disable=unused-variable
        g.request_start_time = datetime.datetime.utcnow()

    @resulting_app.before_request
    def __set_query_durations() -> None:
        g.queries_amount = 0
        g.queries_total_duration = 0
        g.queries_max_duration = None
        g.query_start = None

    @resulting_app.before_request
    @flask_jwt.jwt_optional
    def __set_current_user() -> None:  # pylint: disable=unused-variable
        # This code is necessary to make `flask_jwt_extended` understand that
        # we always want to try to load the given JWT token. The function body
        # SHOULD be empty here.
        pass

    @resulting_app.teardown_request
    def __teardown_request(exception: t.Type[Exception]) -> None:  # pylint: disable=unused-variable
        if exception:  # pragma: no cover
            models.db.session.expire_all()
            models.db.session.rollback()

    # Configurations
    resulting_app.config.update(global_config.CONFIG)
    resulting_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    if config is not None:  # pragma: no cover
        resulting_app.config.update(config)

    if (
        resulting_app.config['SECRET_KEY'] is None or
        resulting_app.config['LTI_SECRET_KEY'] is None
    ):  # pragma: no cover
        raise ValueError('The option to generate keys has been removed')

    @resulting_app.before_request
    def __create_logger() -> None:  # pylint: disable=unused-variable
        g.request_id = uuid.uuid4()
        log = logger.new(
            request_id=str(g.request_id),
            current_user=current_user and current_user.username,
            path=flask.request.path,
            view=getattr(flask.request.url_rule, 'rule', None),
            base_url=resulting_app.config['EXTERNAL_URL'],
        )
        log.info(
            "Request started", host=request.host_url, method=request.method
        )

    @event.listens_for(Engine, "before_cursor_execute")
    def __before_cursor_execute(*_args: object) -> None:
        if hasattr(g, 'query_start'):
            g.query_start = datetime.datetime.utcnow()

    @event.listens_for(Engine, "after_cursor_execute")
    def __after_cursor_execute(*_args: object) -> None:
        if hasattr(g, 'queries_amount'):
            g.queries_amount += 1
        if hasattr(g, 'query_start'):
            delta = (datetime.datetime.utcnow() -
                     g.query_start).total_seconds()
            if hasattr(g, 'queries_total_duration'):
                g.queries_total_duration += delta
            if (
                hasattr(g, 'queries_max_duration') and (
                    g.queries_max_duration is None or
                    delta > g.queries_max_duration
                )
            ):
                g.queries_max_duration = delta

    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.format_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ]
    structlog.configure(
        processors=processors,
        context_class=structlog.threadlocal.wrap_dict(dict),
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    if getattr(resulting_app, 'debug', False):
        structlog.configure(
            processors=processors[:-2] + [
                structlog.dev.ConsoleRenderer(
                    colors=not getattr(resulting_app, 'testing', False)
                )
            ]
        )
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
    )
    logging.getLogger('psef').setLevel(logging.DEBUG)
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    # Let the celery logger shut up
    logging.getLogger('celery').propagate = False

    @resulting_app.errorhandler(RateLimitExceeded)
    def __handle_error(_: RateLimitExceeded) -> 'flask.Response':  # pylint: disable=unused-variable
        res = jsonify(
            errors.APIException(
                'Rate limit exceeded, slow down!',
                'Rate limit is exceeded',
                errors.APICodes.RATE_LIMIT_EXCEEDED,
                429,
            )
        )
        res.status_code = 429
        return res

    limiter.init_app(resulting_app)

    from . import auth
    auth.init_app(resulting_app)

    from . import parsers
    parsers.init_app(resulting_app)

    from . import models
    models.init_app(resulting_app)

    from . import mail
    mail.init_app(resulting_app)

    from . import errors
    errors.init_app(resulting_app)

    from . import tasks
    tasks.init_app(resulting_app)

    from . import json_encoders
    json_encoders.init_app(resulting_app)

    from . import files
    files.init_app(resulting_app)

    from . import lti
    lti.init_app(resulting_app)

    from . import helpers
    helpers.init_app(resulting_app)

    from . import linters
    linters.init_app(resulting_app)

    # Register blueprint(s)
    from . import v1 as api_v1
    api_v1.init_app(resulting_app)

    from . import plagiarism
    plagiarism.init_app(resulting_app)

    # Make sure celery is working
    if not skip_celery:  # pragma: no cover
        try:
            tasks.add(2, 3)
        except Exception:  # pragma: no cover
            print(  # pylint: disable=bad-builtin
                'Celery is not responding! Please check your config',
                file=sys.stderr
            )
            raise

    typ = t.TypeVar('typ')

    @resulting_app.after_request
    def __after_request(res: typ) -> typ:  # pylint: disable=unused-variable
        queries_amount = g.queries_amount
        queries_total_duration = g.queries_total_duration
        queries_max_duration = g.queries_max_duration or 0
        log_msg = (
            logger.info if queries_max_duration < 0.5 and queries_amount < 20
            else logger.warning
        )
        end_time = datetime.datetime.utcnow()
        log_msg(
            'Request finished',
            request_time=str(end_time - g.request_start_time),
            status_code=getattr(res, 'status_code', None),
            queries_amount=queries_amount,
            queries_total_duration=queries_total_duration,
            queries_max_duration=queries_max_duration
        )
        return res

    return resulting_app
