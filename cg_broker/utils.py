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
    return current_task.maybe_delay_task(wanted_time)
