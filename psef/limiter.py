"""This module is a typesafe wrapper around Flask-Limiter

SPDX-License-Identifier: AGPL-3.0-only
"""
import typing as t

from flask import Response
from flask_limiter import Limiter, RateLimitExceeded

from cg_json import JSONResponse

from . import errors

if t.TYPE_CHECKING:
    from . import PsefFlask  # pylint: disable=unused-import


def _limiter_key_func() -> None:  # pragma: no cover
    """This is the default key function for the limiter.

    The key function should be set locally at every place the limiter is used
    so this function always raises a :py:exc:`ValueError`.
    """
    raise ValueError('Key function should be overridden')


def _limiter_deduct_when(response: Response) -> bool:
    return response.status_code >= 400


_LIMITER = Limiter(
    key_func=_limiter_key_func,
    default_limits_deduct_when=_limiter_deduct_when
)


def init_app(app: 'PsefFlask') -> None:
    def _handle_rate_limit_exceeded(_: RateLimitExceeded
                                    ) -> JSONResponse[errors.APIException]:
        return JSONResponse.make(
            errors.APIException(
                'Rate limit exceeded, slow down!',
                'Rate limit is exceeded',
                errors.APICodes.RATE_LIMIT_EXCEEDED,
                429,
            ),
            429,
        )

    app.errorhandler(RateLimitExceeded)(_handle_rate_limit_exceeded)
    _LIMITER.init_app(app)


T_CAL = t.TypeVar('T_CAL', bound=t.Callable)


def limit(
    amount: str,
    *,
    key_func: t.Callable[[], object],
    deduct_on_err_only: bool = False,
) -> t.Callable[[T_CAL], T_CAL]:
    return _LIMITER.limit(
        amount,
        key_func=key_func,
        deduct_when=(_limiter_deduct_when if deduct_on_err_only else None)
    )
