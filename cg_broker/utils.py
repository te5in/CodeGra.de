"""This file contains utility functions for the broker.

SPDX-License-Identifier: AGPL-3.0-only
"""
import secrets
from datetime import datetime

import structlog
from celery import current_task

logger = structlog.get_logger()

_PASS_LEN = 64


def make_password(nbytes: int = _PASS_LEN) -> str:
    """Generate a secure password.

    :param nbytes: Amount of bytes the password should be long, has to be > 32.
    :returns: A generated secure password.
    """
    assert nbytes > 32, 'Not secure enough'
    return secrets.token_hex(_PASS_LEN)


def maybe_delay_current_task(wanted_time: datetime) -> bool:
    """Maybe delay the currently executing task.

    This function reschedules the current task with the same arguments if the
    current time is before the given wanted time.

    :param wanted_time: The earliest time the current task may be executed.
    :returns: ``True`` if the task was rescheduled, in this case you should
        quit running the current task.
    """
    assert current_task
    now = datetime.utcnow()

    logger.info(
        'Checking if should delay the task',
        wanted_time=wanted_time.isoformat(),
        current_time=now.isoformat(),
        should_delay=now < wanted_time,
    )

    if now >= wanted_time:
        return False

    logger.info(
        'Delaying task',
        wanted_time=wanted_time.isoformat(),
        current_time=now.isoformat(),
    )
    current_task.apply_async(
        args=current_task.request.args,
        kwargs=current_task.request.kwargs,
        eta=wanted_time
    )
    return True
