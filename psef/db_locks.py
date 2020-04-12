"""
This module is in charge of managing namespaced user level database locks.

Please only use this locks if row level locking is not possible, for example if
it is possible that a row doesn't exist just yet.

SPDX-License-Identifier: AGPL-3.0-only
"""
import enum

import sqlalchemy

import psef


@enum.unique
class LockNamespaces(enum.Enum):
    """Possible namespaces for the user level locks.

    .. note::

        Make sure that the highest value never exceeds 2 **
        ``NAMESPACE_RESERVE_BITS``, as locks might start colliding in that
        case.
    """
    comment_base = 1


NAMESPACE_RESERVE_BITS = 8
MAX_LOCK_VALUE = 2 ** 63
MAX_GIVEN_VALUE = MAX_LOCK_VALUE >> NAMESPACE_RESERVE_BITS


def acquire_lock(namespace: LockNamespaces, value: int) -> None:
    """Acquire a database user level lock in the given namespace.

    :returns: Nothing, the lock will be released at the end of the transaction.
    """
    assert value > 0, 'Value should be a positive number'
    assert value < MAX_GIVEN_VALUE, 'Max value should not be exceeded'

    to_lock = namespace.value | (value << 8)
    assert to_lock < MAX_LOCK_VALUE

    psef.models.db.session.execute(
        sqlalchemy.select([sqlalchemy.func.pg_advisory_xact_lock(to_lock)])
    )
