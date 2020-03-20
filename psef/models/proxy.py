"""This module defines all models needed for proxies

SPDX-License-Identifier: AGPL-3.0-only
"""
import enum
import typing as t
import secrets
import datetime
from uuid import UUID
from collections import defaultdict

from sqlalchemy_utils import UUIDType

from cg_sqlalchemy_helpers.mixins import UUIDMixin, TimestampMixin

from . import (
    Base, File, MyQuery, FileOwner, NestedFileMixin, AutoTestOutputFile, db
)
from .. import app, helpers
from ..cache import cache_within_request
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


class ProxyState(enum.IntEnum):
    """The state that a proxy is in.
    """
    before_post = 0
    in_use = 1
    deleted = 2


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
    __tablename__ = 'proxy'

    state = db.Column(
        'state',
        db.Enum(ProxyState),
        nullable=False,
        default=ProxyState.before_post,
        server_default='before_post',
    )
    _password = db.Column(
        'password',
        db.Unicode,
        nullable=False,
        default=secrets.token_hex,
    )

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
    def password(self) -> str:
        """Get the password of this proxy.

        .. warning::

            Only compare with this password using a method like
            :meth:`hmac.compare_digest`
        """
        return self._password

    @property
    def deleted(self) -> bool:
        """Is this proxy deleted
        """
        if self.state == ProxyState.deleted:
            return True
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
        >>> open.csp_header == "default-src * data: 'unsafe-eval' 'unsafe-inline'"
        True
        >>> liberal.csp_header != open.csp_header
        True
        >>> liberal.csp_header != strict.csp_header
        True
        """
        self_src = "'self'"
        base_domain = app and app.config['PROXY_BASE_DOMAIN']
        if base_domain:  # pragma: no cover
            self_src += f" https://{self.id}.{base_domain}"

        if not self.allow_remote_resources:
            return f"default-src {self_src} 'unsafe-inline'"
        elif not self.allow_remote_scripts:
            return (
                f"default-src {self_src} 'unsafe-inline';"
                " style-src * 'unsafe-inline';"
                " font-src * 'unsafe-inline';"
                " img-src * 'unsafe-inline' data:;"
                " media-src * 'unsafe-inline'"
            )
        else:
            return "default-src * data: 'unsafe-eval' 'unsafe-inline'"

    @property
    def expired(self) -> bool:
        """Is this proxy expired.
        """
        return (
            helpers.get_request_start_time() - self.created_at > self.max_age
        )

    def __to_json__(self) -> t.Mapping[str, str]:
        return {'id': str(self.id)}

    @cache_within_request
    def _get_at_file_lookup(
        self
    ) -> t.Mapping[t.Optional[UUID], t.Mapping[str, UUID]]:
        base = self.base_at_result_file
        assert base is not None

        lookup: t.MutableMapping[t.Optional[UUID], t.
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

        return lookup

    def _get_at_file(self, path: t.Sequence[str]
                     ) -> t.Optional[NestedFileMixin[UUID]]:
        base = self.base_at_result_file
        assert base is not None

        lookup = self._get_at_file_lookup()

        found_id = _search_candiate(lookup, base, path)
        if found_id is None:
            return None
        return AutoTestOutputFile.query.get(found_id)

    @cache_within_request
    def _get_work_file_lookup(
        self
    ) -> t.Mapping[t.Optional[int], t.Dict[str, int]]:
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

        return lookup

    def _get_work_file(self, path: t.Sequence[str]
                       ) -> t.Optional[NestedFileMixin[int]]:
        base = self.base_work_file
        assert base is not None
        lookup = self._get_work_file_lookup()

        found_id = _search_candiate(lookup, base, path)
        if found_id is None:
            return None
        return File.query.get(found_id)

    def get_file(
        self, path: t.Sequence[str], *, dir_ok: bool
    ) -> t.Union[None, NestedFileMixin[int], NestedFileMixin[UUID]]:
        """Get a file from this proxy for the given path.

        :param path: The path to search for.
        :returns: The found file, or ``None``.
        """
        assert not self.expired
        assert not self.deleted
        res: t.Union[None, NestedFileMixin[int], NestedFileMixin[UUID]]

        if self.base_at_result_file_id is None:
            res = self._get_work_file(path)
        else:
            res = self._get_at_file(path)

        if res is None or (res.is_directory and not dir_ok):
            return None
        return res
