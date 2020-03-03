"""This module defines all models needed for proxies

SPDX-License-Identifier: AGPL-3.0-only
"""
import typing as t
import datetime
from uuid import UUID
from collections import defaultdict

from sqlalchemy_utils import UUIDType

from cg_sqlalchemy_helpers.mixins import UUIDMixin, TimestampMixin

from . import (
    Base, File, MyQuery, FileOwner, NestedFileMixin, AutoTestOutputFile, db
)
from .. import helpers
from ..exceptions import APICodes, APIException

T = t.TypeVar('T')


def _search_candiate(
    lookup: t.Mapping[t.Optional[T], t.Mapping[str, T]],
    base_file: NestedFileMixin[T],
    path: t.Sequence[str],
) -> t.Optional[T]:
    """
    """
    try:
        cur = base_file.get_id()
        for wanted_name in path:
            cur = lookup[cur][wanted_name]
        return cur
    except KeyError:
        return None


class Proxy(Base, UUIDMixin, TimestampMixin):
    """A proxy, which can be used to get files from an AutoTest result or a
    submission for a limited time without authentication.

    :ivar base_work_file_id: The id of the base file from which this proxy
        serves files.
    :ivar base_at_result_file_id: The id of the base file from which this proxy
        serves files. Exactly one of ``base_work_file_id`` and
        ``base_at_result_file_id`` is ``None``.
    :ivar excluding_fileowner: The file owner which should not be served using
        this proxy. This is never ``None`` if ``base_work_file_id`` is not
        ``None``, and always ``None`` otherwise.
    """
    if t.TYPE_CHECKING:  # pragma: no cover
        query: t.ClassVar[MyQuery['Proxy']]
    __tablename__ = 'proxy'

    max_age = db.Column(
        'max_age',
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
    base_work_file = db.relationship(File, foreign_keys=base_work_file_id)

    base_at_result_file_id = db.Column(
        'base_at_result_file_id',
        UUIDType,
        db.ForeignKey('auto_test_output_file.id', ondelete='CASCADE'),
        nullable=True,
    )
    base_at_result_file = db.relationship(
        AutoTestOutputFile, foreign_keys=base_at_result_file_id
    )

    excluding_fileowner = db.Column(
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
            (
                '(base_at_result_file_id is NULL) or'
                ' (excluding_fileowner is NULL)'
            ),
            name='fileowner_null_iff_work_file_id_null'
        ),
    )

    @t.overload
    def __init__(
        self,
        *,
        base_at_result_file: AutoTestOutputFile,
        allow_remote_resources: bool,
        allow_remote_scripts: bool,
    ) -> None:  # pragma: no cover
        pass

    @t.overload
    def __init__(
        self,
        *,
        base_work_file: File,
        excluding_fileowner: FileOwner,
        allow_remote_resources: bool,
        allow_remote_scripts: bool,
    ) -> None:  # pragma: no cover
        pass

    def __init__(
        self, *, allow_remote_resources: bool, allow_remote_scripts: bool,
        **kwargs: object
    ) -> None:
        if allow_remote_scripts and not allow_remote_resources:
            raise APIException(
                (
                    'The value "allow_remote_scripts" can only be true if'
                    ' "allow_remote_resources" is true.'
                ), (
                    'Invalid combination of remote_scripts and'
                    ' remote_resources found'
                ), APICodes.INVALID_PARAM, 400
            )
        super().__init__(
            **kwargs,
            allow_remote_resources=allow_remote_resources,
            allow_remote_scripts=allow_remote_scripts
        )

    @property
    def deleted(self) -> bool:
        """Is this proxy deleted
        """
        if self.base_work_file is None:
            return False
        return self.base_work_file.work.deleted

    @property
    def csp_header(self) -> str:
        """Get the csp header for this proxy.

        >>> strict = Proxy(allow_remote_resources=False,
        ...  allow_remote_scripts=False)
        >>> liberal = Proxy(allow_remote_resources=True,
        ...  allow_remote_scripts=False)
        >>> open = Proxy(allow_remote_resources=True,
        ...  allow_remote_scripts=True)
        >>> strict.csp_header == "default-src 'self' 'unsafe-inline'"
        True
        >>> open.csp_header == "default-src * 'unsafe-eval' 'unsafe-inline'"
        True
        >>> liberal.csp_header != open.csp_header
        True
        >>> liberal.csp_header != strict.csp_header
        True
        """
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
        """Is this proxy expired.
        """
        return (
            helpers.get_request_start_time() - self.created_at > self.max_age
        )

    def __to_json__(self) -> t.Mapping[str, str]:
        return {'id': str(self.id)}

    def _get_at_file(self, path: t.Sequence[str]
                     ) -> t.Optional[NestedFileMixin[UUID]]:
        base = self.base_at_result_file
        assert base is not None

        lookup: t.Mapping[t.Optional[UUID], t.
                          Dict[str, UUID]] = defaultdict(dict)

        for f_id, f_name, f_parent_id in db.session.query(
            AutoTestOutputFile.id,
            AutoTestOutputFile.name,
            AutoTestOutputFile.parent_id,
        ).filter(
            AutoTestOutputFile.suite == base.suite,
            AutoTestOutputFile.result == base.result,
        ):
            lookup[f_parent_id][f_name] = f_id

        found_id = _search_candiate(lookup, base, path)
        if found_id is None:
            return None
        return AutoTestOutputFile.query.get(found_id)

    def _get_work_file(self, path: t.Sequence[str]
                       ) -> t.Optional[NestedFileMixin[int]]:
        base = self.base_work_file
        assert base is not None
        assert self.excluding_fileowner is not None

        lookup: t.Mapping[t.Optional[int], t.
                          Dict[str, int]] = defaultdict(dict)
        for f_id, f_name, f_parent_id in db.session.query(
            File.id, File.name, File.parent_id
        ).filter(
            File.work == base.work,
            File.fileowner != self.excluding_fileowner,
        ):
            lookup[f_parent_id][f_name] = f_id

        found_id = _search_candiate(lookup, base, path)
        if found_id is None:
            return None
        return File.query.get(found_id)

    def get_file(
        self, path: t.Sequence[str]
    ) -> t.Union[None, NestedFileMixin[int], NestedFileMixin[UUID]]:
        """Get a file from this proxy for the given path.

        :param path: The path to search for.
        :returns: The found file, or ``None``.
        """
        assert not self.expired
        assert not self.deleted

        if not path:
            return None
        elif self.base_at_result_file_id is None:
            return self._get_work_file(path)
        else:
            return self._get_at_file(path)
