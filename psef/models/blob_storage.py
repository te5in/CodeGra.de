"""This module defines a models to store some binary data in the database.

Do not use these blobs for things like file storage, but only for temporary
storage of data. The only use as of writing is temporary storing of lti launch
data.

SPDX-License-Identifier: AGPL-3.0-only
"""

from cg_sqlalchemy_helpers.mixins import UUIDMixin, TimestampMixin

from . import Base, db


class BlobStorage(Base, UUIDMixin, TimestampMixin):
    """This class represents a blob indexed by a uuid.

    :ivar data: The data that is stored in this blob.
    """
    data = db.Column('data', db.LargeBinary, nullable=False)

    def __init__(self, *, data: bytes) -> None:
        super().__init__(data=data)
