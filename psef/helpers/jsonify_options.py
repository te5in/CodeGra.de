"""This module makes it possible to give options for the jsonification of
models.

SPDX-License-Identifier: AGPL-3.0-only
"""
import dataclasses

import flask


@dataclasses.dataclass
class Options:
    """Options used for jsonification.
    """
    latest_only: bool = False


def get_options() -> Options:
    """Get a mutable options object.
    """
    if not hasattr(flask.g, 'jsonify_options'):
        flask.g.jsonify_options = Options()
    return flask.g.jsonify_options
