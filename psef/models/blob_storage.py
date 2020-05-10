"""This module defines a models to store some binary data in the database.

Do not use these blobs for things like file storage, but only for temporary
storage of data. The only use as of writing is temporary storing of lti launch
data.

SPDX-License-Identifier: AGPL-3.0-only
"""

import json as _json
import typing as t
import datetime

from typing_extensions import Literal

import psef
from cg_sqlalchemy_helpers.mixins import UUIDMixin, TimestampMixin

from . import Base, db


class BlobStorage(Base, UUIDMixin, TimestampMixin):
    """This class represents a blob indexed by a uuid.

    :ivar data: The data that is stored in this blob.
    """
    data = db.Column('data', db.LargeBinary, nullable=False)

    @t.overload
    def __init__(self, *, data: bytes) -> None:
        ...

    @t.overload
    def __init__(self, *, json: 'psef.helpers.JSONType') -> None:
        ...

    def __init__(
        self, *, data: bytes = None, json: 'psef.helpers.JSONType' = None
    ) -> None:
        self._parsed_json: t.Union[Literal[psef.helpers.UnsetType.token],
                                   'psef.helpers.JSONType',
                                   ] = psef.helpers.UNSET
        if data is None:
            assert json is not None
            data = _json.dumps(json).encode('utf8')
        super().__init__(data=data)

    @property
    def age(self) -> datetime.timedelta:
        return psef.helpers.get_request_start_time() - self.created_at

    def as_json(self) -> 'psef.helpers.JSONType':
        # If the model is loaded from the database the `__init__` method is not
        # called, so the `_parsed_json` attribute doesn't exist at this point.
        unset = psef.helpers.UNSET
        if getattr(self, '_parsed_json', unset) is unset:
            self._parsed_json = _json.loads(self.data.decode('utf8'))
        # Mypy doesn't understand the magic with `getattr` above
        return t.cast(t.Any, self._parsed_json)
