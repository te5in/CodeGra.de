"""This module implements the handling of LTI messages.

It contains two submodules for the supported LTI version: :mod:`.v1_1` for LTI
version 1.1 and :mod:`.v1_3` for LTI version 1.3.

SPDX-License-Identifier: AGPL-3.0-only
"""
import enum
import typing as t

from .. import PsefFlask

__all__: t.List[str] = []


class LTIVersion(enum.Enum):
    """The supported LTI version.
    """
    v1_1 = enum.auto()
    v1_3 = enum.auto()

    def __to_json__(self) -> str:
        return self.name


def init_app(app: PsefFlask) -> None:
    """Initialize LTI for the given flask app.
    """
    # This import is here to break some cyclic imports.
    from . import v1_1, v1_3  # pylint: disable=import-outside-toplevel
    v1_1.init_app(app)
    v1_3.init_app(app)
