"""This module defines caching utilities to be used inside CodeGrade.

The submodule ``inter_request`` for caching utilities between different
requests and ``intra_request`` for caching within a single request.

SPDX-License-Identifier: AGPL-3.0-only
"""
import flask

from . import inter_request, intra_request


def init_app(app: flask.Flask) -> None:
    """Setup caching for the given app.
    """
    inter_request.init_app(app)
    intra_request.init_app(app)
