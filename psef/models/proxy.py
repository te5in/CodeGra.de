"""This module defines all models needed for proxies

SPDX-License-Identifier: AGPL-3.0-only
"""
import uuid
import typing as t
import datetime

from sqlalchemy_utils import UUIDType

from cg_sqlalchemy_helpers.mixins import UUIDMixin, TimestampMixin

from . import (
    Base, File, Work, MyQuery, DbColumn, FileOwner, NestedFileMixin,
    AutoTestOutputFile, db
)
from .. import helpers

T = t.TypeVar('T')


def _search_candiate(
    candidates: t.Sequence[NestedFileMixin[T]],
    lookup: t.Mapping[T, t.Tuple[str, T]],
    base_file: NestedFileMixin[T],
    path: t.Sequence[str],
) -> t.Optional[NestedFileMixin[T]]:
    to_search = path[:-1]
    for candidate in candidates:
        next_id = candidate.parent_id
        for wanted_name in reversed(to_search):
            found_name, next_id = lookup[next_id]
            if found_name != wanted_name:
                break
        else:
            # We got to the root dir
            if next_id == base_file.id:
                return candidate

    return None


class Proxy(Base, UUIDMixin, TimestampMixin):
    if t.TYPE_CHECKING:  # pragma: no cover
        query: t.ClassVar[MyQuery['Proxy']]
    __tablename__ = 'proxy'

    deleted = db.Column('deleted', db.Boolean, default=False, nullable=False)
    max_unused_time = db.Column(
        'max_unused_time',
        db.Interval,
        nullable=False,
        default=datetime.timedelta(minutes=30),
    )

    base_work_file_id = db.Column(
        'base_work_file_id',
        db.Integer,
        db.ForeignKey('File.id'),
        nullable=True,
    )
    base_work_file = db.relationship('File', foreign_keys=base_work_file_id)

    base_at_result_file_id = db.Column(
        'base_at_result_file_id',
        UUIDType,
        db.ForeignKey('auto_test_output_file.id'),
        nullable=True
    )
    base_at_result_file = db.relationship(
        'AutoTestOutputFile', foreign_keys=base_at_result_file_id
    )

    @property
    def base_file(self) -> NestedFileMixin:
        return self.base_work_file or self.base_at_result_file

    excluding_fileowner: FileOwner = db.Column(
        'excluding_fileowner',
        db.Enum(FileOwner),
        default=None,
        nullable=True,
    )

    allow_remote_resources = db.Column(
        'allow_remote_resources', db.Boolean, nullable=False
    )
    allow_remote_scripts = db.Column(
        'allow_remote_scripts', db.Boolean, nullable=False
    )

    __table_args__ = (
        db.CheckConstraint(
            'allow_remote_resources or not allow_remote_scripts',
            name='remote_scripts_only_true_when_remote_resources_true'
        ),
        db.CheckConstraint(
            '(base_at_result_file_id is NULL) != (base_work_file_id is NULL)',
            name='either_at_result_file_or_work_file'
        ),
        db.CheckConstraint(
            '(base_at_result_file_id is NULL) or (excluding_fileowner is NULL)',
            name='fileowner_null_iff_work_file_id_null'
        ),
    )

    @property
    def csp_header(self) -> str:
        if not self.allow_remote_resources:
            return "default-src 'self' 'unsafe-inline'"
        elif not self.allow_remote_scripts:
            return (
                "default-src 'self' 'unsafe-inline';"
                " style-src * 'unsafe-inline';"
                " font-src * 'unsafe-inline';"
                " img-src * 'unsafe-inline';"
                " media-src * 'unsafe-inline'"
            )
        else:
            return "default-src * 'unsafe-eval' 'unsafe-inline'"

    @property
    def expired(self) -> bool:
        return (
            self.created_at - helpers.get_request_start_time() >
            self.max_unused_time
        )

    def __to_json__(self) -> t.Mapping[str, str]:
        return {'id': str(self.id)}

    def _get_at_file(self, path: t.Sequence[str]
                     ) -> t.Optional[NestedFileMixin[uuid.UUID]]:
        name = path[-1]

        base = self.base_at_result_file
        assert base is not None

        candidates = AutoTestOutputFile.query.filter(
            AutoTestOutputFile.suite == base.suite,
            AutoTestOutputFile.name == name,
            ~AutoTestOutputFile.is_directory,
        ).all()

        lookup = {
            f_id: (f_name, f_parent_id)
            for f_id, f_name, f_parent_id in db.session.query(
                AutoTestOutputFile.id, AutoTestOutputFile.name,
                AutoTestOutputFile.parent_id
            ).filter(
                AutoTestOutputFile.suite == base.suite,
            )
        }

        return _search_candiate(
            candidates, lookup, self.base_at_result_file, path
        )

    def _get_work_file(self, path: t.Sequence[str]
                       ) -> t.Optional[NestedFileMixin[int]]:
        name = path[-1]

        assert self.base_work_file is not None
        assert self.excluding_fileowner is not None

        candidates = File.query.filter(
            File.work == self.base_work_file.work,
            File.fileowner != self.excluding_fileowner,
            File.name == name,
            ~File.is_directory,
        ).all()

        lookup = {
            f_id: (f_name, f_parent_id)
            for f_id, f_name, f_parent_id in
            db.session.query(File.id, File.name, File.parent_id).filter(
                File.work == self.base_work_file.work,
                File.fileowner != self.excluding_fileowner,
            )
        }

        return _search_candiate(candidates, lookup, self.base_work_file, path)

    def get_file(self,
                 path: t.Sequence[str]) -> t.Optional[NestedFileMixin]:
        if self.base_at_result_file_id is None:
            return self._get_work_file(path)
        else:
            return self._get_at_file(path)
