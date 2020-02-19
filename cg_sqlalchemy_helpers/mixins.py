"""This module implements different useful mixins for SQLAlchemy.

SPDX-License-Identifier: AGPL-3.0-only
"""
import uuid

from sqlalchemy import TIMESTAMP, Column, Integer
from sqlalchemy_utils import UUIDType

from cg_dt_utils import DatetimeWithTimezone

from .types import ColumnProxy

__all__ = ['IdMixin', 'UUIDMixin', 'TimestampMixin']


def _make_uuid() -> uuid.UUID:
    return uuid.uuid4()


class IdMixin:
    """
    Provides the :attr:`id` primary key column
    """
    id: ColumnProxy[int] = Column(Integer, primary_key=True)


class UUIDMixin:
    """
    Provides the :attr:`id` primary key column as a uuid
    """
    id: ColumnProxy[uuid.UUID] = Column(
        UUIDType, primary_key=True, default=_make_uuid
    )


class TimestampMixin:
    """
    Provides the :attr:`created_at` and :attr:`updated_at` audit timestamps
    """
    #: Timestamp for when this instance was created.
    created_at: ColumnProxy[DatetimeWithTimezone] = Column(
        TIMESTAMP(timezone=True),
        default=DatetimeWithTimezone.utcnow,
        nullable=False
    )

    #: Timestamp for when this instance was last updated.
    updated_at: ColumnProxy[DatetimeWithTimezone] = Column(
        TIMESTAMP(timezone=True),
        default=DatetimeWithTimezone.utcnow,
        onupdate=DatetimeWithTimezone.utcnow,
        nullable=False
    )
