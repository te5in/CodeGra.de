"""This module contains functions to deal with features.

SPDX-License-Identifier: AGPL-3.0-only
"""

import enum
import typing as t
from functools import wraps

import structlog

import psef

from .exceptions import FeatureException

logger = structlog.get_logger()

T = t.TypeVar('T')

T_CAL = t.TypeVar('T_CAL', bound=t.Callable)  # pylint: disable=invalid-name


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
    AUTO_TEST = enum.auto()
    COURSE_REGISTER = enum.auto()

    def __to_json__(self) -> t.Mapping[str, str]:
        return {
            'name': self.name,
        }


def ensure_feature(feature: Feature) -> None:
    """Check if a certain feature is enabled.

    :param feature: The feature to check for.
    :returns: Nothing.

    :raises FeatureException: If the feature is not enabled. (DISABLED_FEATURE)
    """
    if not has_feature(feature):
        logger.warning('Tried to use disabled feature', feature=feature.name)
        raise FeatureException(feature)


def has_feature(feature: Feature) -> bool:
    """Check if a certain feature is enabled.

    :param feature: The feature to check for.
    :returns: A boolean indicating if the given feature is enabled
    """
    return psef.app.config['FEATURES'][feature]


def feature_required(feature: Feature) -> t.Callable[[T_CAL], T_CAL]:
    """ A decorator used to make sure the function decorated is only called
    with a certain feature enabled.

    :param feature: The feature to check for.

    :returns: The value of the decorated function if the given feature is
        enabled.

    :raises FeatureException: If the feature is not enabled. (DISABLED_FEATURE)
    """

    def __decorator(f: T_CAL) -> T_CAL:
        @wraps(f)
        def __decorated_function(*args: t.Any, **kwargs: t.Any) -> t.Any:
            ensure_feature(feature)
            return f(*args, **kwargs)

        return t.cast(T_CAL, __decorated_function)

    return __decorator
