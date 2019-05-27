import sys
import uuid
import typing as t
import logging as system_logging
import datetime
import threading

import structlog
import flask_jwt_extended as flask_jwt
from flask import g, request

import psef

logger = structlog.get_logger()

LogCallback = t.Callable[[object, str, str], None]
_logger_callbacks: t.List[LogCallback] = []


def init_app(app: 'psef.PsefFlask') -> None:
    """Initialize the app.

    :param app: The flask app to initialize.
    """
    configure_logging(
        getattr(app, 'debug', False),
        getattr(app, 'testing', False),
    )

    @app.before_request
    def __create_logger() -> None:  # pylint: disable=unused-variable
        g.request_id = uuid.uuid4()
        log = logger.new(
            request_id=str(g.request_id),
            path=request.path,
            view=getattr(request.url_rule, 'rule', None),
            base_url=app.config['EXTERNAL_URL'],
        )
        flask_jwt.verify_jwt_in_request_optional()
        log.bind(current_user=psef.current_user and psef.current_user.username)

        func = log.info
        try:
            start = datetime.datetime.utcfromtimestamp(
                float(request.headers['X-Request-Start-Time'])
            )
            wait_time = (g.request_start_time - start).total_seconds()
            if wait_time > 5:
                log.error
            if wait_time > 1:
                log.warning
            log.bind(time_spend_in_queue=wait_time)
        except:
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


class LoggerCallback:
    def __init__(self, fun: LogCallback) -> None:
        self.fun = fun

    def disable(self) -> None:
        _logger_callbacks.remove(self.fun)


def logger_callback(fun: LogCallback) -> LoggerCallback:
    assert fun not in _logger_callbacks
    _logger_callbacks.append(fun)
    return LoggerCallback(fun)


def configure_logging(debug: bool, testing: bool) -> None:
    json_renderer = structlog.processors.JSONRenderer()

    def add_thread_name(
        logger: object, method_name: object, event_dict: dict
    ) -> dict:
        event_dict['thread_id'] = threading.current_thread().name
        return event_dict

    def log_callbacks(logger: object, method_name: str,
                      event_dict: t.Any) -> t.Dict[str, object]:
        if debug:
            json_event_dict = json_renderer(logger, method_name, event_dict)
        else:
            json_event_dict = event_dict

        for callback in _logger_callbacks:
            try:
                callback(logger, method_name, json_event_dict)
            except Exception as e:
                pass

        return event_dict

    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
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
        logger_factory=structlog.stdlib.LoggerFactory(),
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
    system_logging.getLogger('celery').propagate = False
