"""This module contains functions to deal with features.

SPDX-License-Identifier: AGPL-3.0-only
"""

import enum
import typing as t
from functools import wraps

import structlog

import psef  # pylint: disable=cyclic-import,unused-import

from .exceptions import APICodes, APIException

logger = structlog.get_logger()

T = t.TypeVar('T')


def init_app(app: 'psef.PsefFlask') -> None:
    app.config['FEATURES'] = {
        feat: app.config['__S_FEATURES'][feat.name]
        for feat in Feature
    }


@enum.unique
class Feature(enum.Enum):
    """All features switches for CodeGrade.
    """
    BLACKBOARD_ZIP_UPLOAD = enum.auto()
    RUBRICS = enum.auto()
    AUTOMATIC_LTI_ROLE = enum.auto()
    LTI = enum.auto()
    LINTERS = enum.auto()
    INCREMENTAL_RUBRIC_SUBMISSION = enum.auto()
    REGISTER = enum.auto()
    GROUPS = enum.auto()


def ensure_feature(feature: Feature) -> None:
    """Check if a certain feature is enabled.

    :param feature: The feature to check for.
    :returns: Nothing.

    :raises APIException: If the feature is not enabled. (DISABLED_FEATURE)
    """
    if not has_feature(feature):
        logger.warning('Tried to use disabled feature', feature=feature.name)
        raise APIException(
            'This feature is not enabled for this instance.',
            f'The feature "{feature.name}" is not enabled.',
            APICodes.DISABLED_FEATURE, 400
        )


def has_feature(feature: Feature) -> bool:
    """Check if a certain feature is enabled.

    :param feature: The feature to check for.
    :returns: A boolean indicating if the given feature is enabled
    """
    return psef.app.config['FEATURES'][feature]


def feature_required(feature: Feature) -> t.Callable:
    """ A decorator used to make sure the function decorated is only called
    with a certain feature enabled.

    :param feature: The feature to check for.

    :returns: The value of the decorated function if the given feature is
        enabled.

    :raises APIException: If the feature is not enabled. (DISABLED_FEATURE)
    """

    def __decorator(f: t.Callable) -> t.Callable:
        @wraps(f)
        def __decorated_function(*args: t.Any, **kwargs: t.Any) -> t.Any:
            ensure_feature(feature)
            return f(*args, **kwargs)

        return __decorated_function

    return __decorator
