from datetime import datetime

from . import db


class IdMixin:
    """
    Provides the :attr:`id` primary key column
    """
    id = db.Column(db.Integer, primary_key=True)


class TimestampMixin:
    """
    Provides the :attr:`created_at` and :attr:`updated_at` audit timestamps
    """
    #: Timestamp for when this instance was created.
    created_at = db.Column(
        'created_at', db.DateTime, default=datetime.utcnow, nullable=False
    )

    #: Timestamp for when this instance was last updated.
    updated_at = db.Column(
        'updated_at',
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
