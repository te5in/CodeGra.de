"""This module contains all code needed for logging and its configuration
within CodeGrade.

SPDX-License-Identifier: AGPL-3.0-only
"""
import sys
import uuid
import typing as t
import logging as system_logging
import datetime
import threading
import contextlib
import multiprocessing

import flask
import structlog
import flask_jwt_extended as flask_jwt
from flask import g, request

logger = structlog.get_logger()

LogCallback = t.Callable[[object, str, str], None]
_logger_callbacks: t.List[LogCallback] = []


def _find_first_app_frame_and_name() -> t.Tuple[object, str]:
    """
    Copied from structlog, MIT License
    """
    ignores = ['structlog', 'cg_logger']
    f = sys._getframe()  # pylint: disable=protected-access
    name = f.f_globals.get('__name__') or '?'
    while any(tuple(name.startswith(i) for i in ignores)):
        if f.f_back is None:
            name = '?'
            break
        f = f.f_back
        name = f.f_globals.get('__name__') or '?'
    return f, name


class PrintLogger(structlog.PrintLogger):  # type: ignore
    """This class implements a simple logger that prints its message to stdout.

    This logger also tries to add which methods called the logger.
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = _find_first_app_frame_and_name()[1]
        self._in_err = False

    def msg(self, message: object) -> None:
        try:
            super().msg(message)
        except:  # pylint: disable=bare-except
            if not self._in_err:
                self._in_err = True
                logger.error(
                    'Something when wrong during logging', exc_info=True
                )
                self._in_err = False

    log = debug = info = warn = warning = msg
    fatal = failure = err = error = critical = exception = msg


def init_app(app: flask.Flask, set_user: bool = True) -> None:
    """Initialize the app.

    :param app: The flask app to initialize.
    """
    configure_logging(
        getattr(app, 'debug', False),
        getattr(app, 'testing', False),
    )

    @app.before_request
    def __create_logger() -> None:  # pylint: disable=unused-variable
        g.request_start_time = datetime.datetime.utcnow()

        g.request_id = uuid.uuid4()
        log = logger.new(
            request_id=str(g.request_id),
            path=request.path,
            view=getattr(request.url_rule, 'rule', None),
            base_url=app.config.get('EXTERNAL_URL'),
        )
        if set_user:
            flask_jwt.verify_jwt_in_request_optional()
            log.bind(
                current_user=flask_jwt.current_user and
                flask_jwt.current_user.username
            )

        func = log.info
        try:
            start = datetime.datetime.utcfromtimestamp(
                float(request.headers['X-Request-Start-Time'])
            )
            wait_time = (g.request_start_time - start).total_seconds()
            if wait_time > 5:
                func = log.error
            if wait_time > 1:
                func = log.warning
            log.bind(time_spend_in_queue=wait_time)
        except:  # pylint: disable=bare-except
            pass

        try:
            func(
                "Request started",
                host=request.host_url,
                method=request.method,
                query_args={
                    k: '<PASSWORD>' if k == 'password' else v
                    for k, v in request.args.items()
                },
            )
        finally:
            log.try_unbind('time_spend_in_queue')

    typ = t.TypeVar('typ')

    @app.after_request
    def __after_request(res: typ) -> typ:  # pylint: disable=unused-variable
        queries_amount: int = getattr(g, 'queries_amount', 0)
        queries_total_duration: int = getattr(g, 'queries_total_duration', 0)
        queries_max_duration: int = getattr(g, 'queries_max_duration', 0) or 0
        log_msg = (
            logger.info if queries_max_duration < 0.5 and queries_amount < 20
            else logger.warning
        )

        cache_hits: int = getattr(g, 'cache_hits', 0)
        cache_misses: int = getattr(g, 'cache_misses', 0)

        end_time = datetime.datetime.utcnow()
        start_time = getattr(g, 'request_start_time', end_time)
        log_msg(
            'Request finished',
            request_time=(end_time - start_time).total_seconds(),
            status_code=getattr(res, 'status_code', None),
            queries_amount=queries_amount,
            queries_total_duration=queries_total_duration,
            queries_max_duration=queries_max_duration,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
        )
        return res


class LoggerCallback:
    """A logger callback class.
    """

    def __init__(self, fun: LogCallback) -> None:
        self.fun = fun

    def disable(self) -> None:
        _logger_callbacks.remove(self.fun)


def logger_callback(fun: LogCallback) -> LoggerCallback:
    """Add a function as a logger callback.
    """
    assert fun not in _logger_callbacks
    _logger_callbacks.append(fun)
    return LoggerCallback(fun)


def configure_logging(debug: bool, testing: bool) -> None:
    """Configure the structlog logger.

    :param debug: Are we in a debug environment.
    :param testing: Are we in a testing environment.
    """
    json_renderer = structlog.processors.JSONRenderer()

    def add_thread_name(_: object, __: object, event_dict: dict) -> dict:
        event_dict['thread_id'] = threading.current_thread().name
        event_dict['process_id'] = multiprocessing.current_process().name
        return event_dict

    def log_callbacks(logger_arg: object, method_name: str,
                      event_dict: t.Any) -> t.Dict[str, object]:
        if debug:
            json_event_dict = json_renderer(
                logger_arg, method_name, event_dict
            )
        else:
            json_event_dict = event_dict

        for callback in _logger_callbacks:
            try:
                callback(logger, method_name, json_event_dict)
            except:  # pylint: disable=bare-except
                pass

        return event_dict

    def add_log_level(_: str, method_name: str, event_dict: t.Dict) -> t.Dict:
        """
        Add the log level to the event dict.
        """
        if method_name == "warn":
            # The stdlib has an alias
            method_name = "warning"

        event_dict['level'] = event_dict.pop('__level__', method_name)

        return event_dict

    processors = [
        structlog.stdlib.add_logger_name,
        add_log_level,
        add_thread_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.format_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        json_renderer,
        log_callbacks,
    ]
    structlog.configure(
        processors=processors,
        context_class=structlog.threadlocal.wrap_dict(dict),
        logger_factory=PrintLogger,
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    if debug:
        structlog.configure(
            processors=processors[:-2] +
            [log_callbacks,
             structlog.dev.ConsoleRenderer(colors=not testing)]
        )

    system_logging.basicConfig(
        format='%(message)s',
        stream=sys.stdout,
    )
    system_logging.getLogger('psef').setLevel(system_logging.DEBUG)
    system_logging.getLogger('werkzeug').setLevel(system_logging.ERROR)
    # Let the celery logger shut up
    # system_logging.getLogger('celery').propagate = False


@contextlib.contextmanager
def bound_to_logger(**vals: object) -> t.Generator[None, None, None]:
    """Bind values to logger for a certain block.
    """
    logger.bind(**vals)
    try:
        yield
    finally:
        logger.try_unbind(*vals.keys())
