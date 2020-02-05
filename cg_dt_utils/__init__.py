"""This module defines functions and methods to work with datetime objects.

SPDX-License-Identifier: AGPL-3.0-only
"""
import re
import time
import typing as t
import datetime

__all__ = ['DatetimeWithTimezone', 'now']

if t.TYPE_CHECKING:  # pragma: no cover

    # pylint: disable=all
    class DatetimeWithTimezone:
        max: t.ClassVar['DatetimeWithTimezone']

        @classmethod
        def utcfromtimestamp(cls, timestamp: float) -> 'DatetimeWithTimezone':
            ...

        @classmethod
        def utcnow(cls) -> 'DatetimeWithTimezone':
            ...

        @t.overload
        def __sub__(self, other: 'DatetimeWithTimezone') -> datetime.timedelta:
            ...

        @t.overload
        def __sub__(self, other: datetime.timedelta) -> 'DatetimeWithTimezone':
            ...

        def __sub__(self, other: t.Any) -> t.Any:
            ...

        def __add__(self, other: datetime.timedelta) -> 'DatetimeWithTimezone':
            ...

        def __lt__(self, other: 'DatetimeWithTimezone') -> bool:
            ...

        def __ge__(self, other: 'DatetimeWithTimezone') -> bool:
            ...

        def isoformat(self) -> str:
            ...

        def timestamp(self) -> float:
            ...

        @classmethod
        def fromisoformat(cls, isoformat: str) -> 'DatetimeWithTimezone':
            ...

        @classmethod
        def from_datetime(
            cls, dt: datetime.datetime, default_tz: datetime.timezone
        ) -> 'DatetimeWithTimezone':
            ...

    # pylint: enable=all
else:

    # Warning, this class is not actually used during runtime, and is only
    # present for type checking (to make sure we only use dates with a timezone
    # attached). So do not instantiate it, as this could make it easy to do a
    # `isinstance` check, but feel free to implement real static methods.

    # pylint: disable=invalid-name
    _utc = datetime.timezone.utc
    _utcfromtimestamp = datetime.datetime.utcfromtimestamp

    # pylint: enable=invalid-name


    class DatetimeWithTimezone(datetime.datetime):
        def __new__(self, *args: t.Any, **kwargs: t.Any) -> t.Any:
            raise Exception(
                'Do not create new "DatetimeWithTimezone" instances'
            )

        @staticmethod
        def utcfromtimestamp(timestamp: float) -> 'DatetimeWithTimezone':
            return _utcfromtimestamp(timestamp).replace(tzinfo=_utc)

        @classmethod
        def utcnow(cls) -> 'DatetimeWithTimezone':
            return cls.utcfromtimestamp(time.time())

        @classmethod
        def fromisoformat(cls, isoformat: str) -> 'DatetimeWithTimezone':
            if re.search(r'([+-]\d\d(:?\d\d)?|Z)$', isoformat) is None:
                isoformat += '+00:00'
            dt = datetime.datetime.fromisoformat(isoformat)
            # This assumes that datetimes without tzinfo are in UTC.
            return cls.utcfromtimestamp(dt.timestamp())

        @staticmethod
        def from_datetime(
            dt: datetime.datetime, default_tz: datetime.timezone
        ) -> 'DatetimeWithTimezone':
            if dt.tzinfo is None:
                # Replace returns a new object.
                dt = dt.replace(tzinfo=default_tz)
            return dt

    DatetimeWithTimezone.max = datetime.datetime.max.replace(tzinfo=_utc)


def now() -> DatetimeWithTimezone:
    return DatetimeWithTimezone.utcnow()
