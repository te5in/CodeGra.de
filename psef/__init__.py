"""
This package implements the backend for codegrade. Because of historic reasons
this backend is named ``psef``.

SPDX-License-Identifier: AGPL-3.0-only
"""
import os
import json as system_json
import uuid
import types
import typing as t
import datetime

import structlog
import flask_jwt_extended as flask_jwt
from flask import Response, g, request
from flask_limiter import Limiter, RateLimitExceeded
from werkzeug.local import LocalProxy

import cg_logger
from cg_json import jsonify

if t.TYPE_CHECKING and getattr(
    t, 'SPHINX', False
) is not True:  # pragma: no cover
    from config import FlaskConfig
    from flask import Flask
    from json import JSONEncoder

    current_app: 'psef.Flask'
else:
    from flask import Flask, current_app  # type: ignore


class PsefFlask(Flask):
    """Our subclass of flask.

    This contains the extra property :meth:`.PsefFlask.do_sanity_checks`.
    """
    config: 'FlaskConfig'  # type: ignore

    def __init__(self, name: str) -> None:
        super().__init__(name)
        with open(
            os.path.join(
                os.path.dirname(__file__), '..', 'seed_data',
                'auto_test_base_systems.json'
            ), 'r'
        ) as f:
            self.auto_test_base_systems = {
                val['id']: val
                for val in system_json.load(f)
            }

    @property
    def max_single_file_size(self) -> 'psef.archive.FileSize':
        """The maximum allowed size for a single file.
        """
        return self.config['MAX_FILE_SIZE']

    @property
    def max_file_size(self) -> 'psef.archive.FileSize':
        """The maximum allowed size for normal files.

        .. note:: An individual file has a different limit!
        """
        return self.config['MAX_NORMAL_UPLOAD_SIZE']

    @property
    def max_large_file_size(self) -> 'psef.archive.FileSize':
        """The maximum allowed size for large files (such as blackboard zips).

        .. note:: An individual file has a different limit!
        """
        return self.config['MAX_LARGE_UPLOAD_SIZE']

    @property
    def do_sanity_checks(self) -> bool:
        """Should we do sanity checks for this app.

        :returns: ``True`` if ``debug`` or ``testing`` is enabled.
        """
        return getattr(self, 'debug', False) or getattr(self, 'testing', False)


logger = structlog.get_logger()

app: 'PsefFlask' = current_app  # pylint: disable=invalid-name

_current_tester = None
current_tester = LocalProxy(lambda: _current_tester)


def enable_testing() -> None:
    global _current_tester
    _current_tester = True


if t.TYPE_CHECKING:  # pragma: no cover
    import psef.models
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


def create_app(  # pylint: disable=too-many-statements
    config: t.Mapping = None,
    skip_celery: bool = False,
    skip_perm_check: bool = True,
    skip_secret_key_check: bool = False,
) -> 'PsefFlask':
    """Create a new psef app.

    :param config: The config mapping that can be used to override config.
    :param skip_celery: Set to true to disable sanity checks for celery.
    :returns: A new psef app object.
    """
    import config as global_config

    resulting_app = PsefFlask(__name__)
    resulting_app.config.update(t.cast(t.Any, global_config.CONFIG))
    resulting_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'  # type: ignore
                         ] = False

    if not resulting_app.debug:
        assert not app.config['AUTO_TEST_DISABLE_ORIGIN_CHECK']

    @resulting_app.before_request
    def __set_request_start_time() -> None:  # pylint: disable=unused-variable
        assert current_tester._get_current_object() is None
        g.request_start_time = datetime.datetime.utcnow()

    if config is not None:  # pragma: no cover
        resulting_app.config.update(config)  # type: ignore

    if (
        not skip_secret_key_check and (
            resulting_app.config['SECRET_KEY'] is None or
            resulting_app.config['LTI_SECRET_KEY'] is None
        )
    ):  # pragma: no cover
        raise ValueError('The option to generate keys has been removed')

    @resulting_app.errorhandler(RateLimitExceeded)
    def __handle_error(_: RateLimitExceeded) -> Response:  # pylint: disable=unused-variable
        res = t.cast(
            Response,
            jsonify(
                errors.APIException(
                    'Rate limit exceeded, slow down!',
                    'Rate limit is exceeded',
                    errors.APICodes.RATE_LIMIT_EXCEEDED,
                    429,
                )
            )
        )
        res.status_code = 429
        return res

    limiter.init_app(resulting_app)

    cg_logger.init_app(resulting_app)

    from . import permissions
    permissions.init_app(resulting_app, skip_perm_check)

    from . import cache
    cache.init_app(resulting_app)

    from . import features
    features.init_app(resulting_app)

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

    from . import files
    files.init_app(resulting_app)

    from . import lti
    lti.init_app(resulting_app)

    from . import auto_test
    auto_test.init_app(resulting_app)

    from . import helpers
    helpers.init_app(resulting_app)

    from . import linters
    linters.init_app(resulting_app)

    from . import plagiarism
    plagiarism.init_app(resulting_app)

    # Register blueprint(s)
    from . import v1 as api_v1
    api_v1.init_app(resulting_app)

    from . import v_internal as api_v_internal
    api_v_internal.init_app(resulting_app)

    # Make sure celery is working
    if not skip_celery:  # pragma: no cover
        try:
            tasks.add(2, 3)
        except Exception:  # pragma: no cover
            logger.error(
                'Celery is not responding! Please check your config',
            )
            raise

    typ = t.TypeVar('typ')

    @resulting_app.after_request
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

    return resulting_app
