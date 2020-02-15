"""
This module DOES NOT define any thing. It is only used for type information
about sqlalchemy.

SPDX-License-Identifier: AGPL-3.0-only
"""
import enum
import typing as t
# pylint: skip-file
from uuid import UUID
from typing import Union
from typing import Optional as Opt
from datetime import timedelta

from typing_extensions import Literal

import cg_dt_utils

T = t.TypeVar('T')
Z = t.TypeVar('Z')
Y = t.TypeVar('Y')
U = t.TypeVar('U')
E = t.TypeVar('E', bound=enum.Enum)
DbSelf = t.TypeVar('DbSelf', bound='MyDb')
QuerySelf = t.TypeVar('QuerySelf', bound='MyNonOrderableQuery')
_T_BASE = t.TypeVar('_T_BASE', bound='Base')


class Comparator:  # pragma: no cover
    def __init__(self, column: 'DbColumn[T]') -> None:
        ...

    def __eq__(self, other: object) -> bool:
        ...

    def __clause_element__(self) -> object:
        ...


class MySession:  # pragma: no cover
    def bulk_save_objects(self, objs: t.Sequence['Base']) -> None:
        ...

    def execute(self, query: object) -> object:
        ...

    @t.overload
    def query(self, __x: 'DbColumn[T]') -> 'MyQueryTuple[T]':
        ...

    @t.overload  # NOQA
    def query(self, __x: 'RawTable') -> 'MyQuery[RawTable]':
        ...

    @t.overload  # NOQA
    def query(self, __x: t.Type[_T_BASE]) -> 'MyQuery[_T_BASE]':
        ...

    @t.overload  # NOQA
    def query(
        self,
        __y: 'DbColumn[T]',
        __x: t.Type[_T_BASE],
    ) -> 'MyQuery[t.Tuple[T, _T_BASE]]':
        ...

    @t.overload  # NOQA
    def query(
        self,
        __y: 'DbColumn[T]',
        __x: 'DbColumn[Z]',
    ) -> 'MyQuery[t.Tuple[T, Z]]':
        ...

    @t.overload  # NOQA
    def query(
        self, __x: t.Type[T], __y: 'DbColumn[Z]'
    ) -> 'MyQuery[t.Tuple[T, Z]]':
        ...

    @t.overload  # NOQA
    def query(
        self, __x: t.Type[T], __y: t.Type[Z]
    ) -> 'MyQuery[t.Tuple[T, Z]]':
        ...

    @t.overload  # NOQA
    def query(
        self,
        __x: T,
        __y: Z,
        __z: Y,
    ) -> 'MyQuery[t.Tuple[T, Z, Y]]':
        ...

    @t.overload  # NOQA
    def query(
        self,
        __x: T,
        __y: Z,
        __z: Y,
        __j: U,
    ) -> 'MyQuery[t.Tuple[T, Z, Y, U]]':
        ...

    def query(self, *args: t.Any) -> 'MyQuery[t.Any]':  # NOQA
        ...

    def add(self, arg: 'Base') -> None:
        ...

    def add_all(self, arg: t.Sequence['Base']) -> None:
        ...

    def flush(self) -> None:
        ...

    def commit(self) -> None:
        ...

    def delete(self, arg: 'Base') -> None:
        ...

    def expunge(self, arg: 'Base') -> None:
        ...

    def expire_all(self) -> None:
        ...

    def rollback(self) -> None:
        ...

    def begin_nested(self) -> t.ContextManager:
        ...


class DbType(t.Generic[T]):  # pragma: no cover
    ...


class RawTable:  # pragma: no cover
    c: t.Any


class _ForeignKey:  # pragma: no cover
    ...


class ImmutableColumnProxy(t.Generic[T]):
    @t.overload
    def __get__(self, _: None, owner: t.Type[object]) -> 'DbColumn[T]':
        ...

    @t.overload
    def __get__(self, _: Z, owner: t.Type[Z]) -> 'T':
        ...

    def __get__(self, *args: t.Any, **kwargs: t.Any) -> t.Any:
        ...


class MutableColumnProxy(t.Generic[T, Y], ImmutableColumnProxy[T]):
    def __set__(self, instance: object, value: Y) -> None:
        ...


class ColumnProxy(t.Generic[T], MutableColumnProxy[T, T]):
    ...


_CP = ColumnProxy


class _Backref:
    ...


class MyDb:  # pragma: no cover
    session: MySession
    Float: DbType[float]
    Integer: DbType[int]
    Unicode: DbType[str]
    Boolean: DbType[bool]
    String: t.Callable[[DbSelf, int], DbType[str]]
    LargeBinary: DbType[bytes]
    Interval: DbType[timedelta]
    init_app: t.Callable
    engine: t.Any

    def ForeignKey(
        self,
        _name: str,
        *,
        ondelete: (t.Union[None, Literal['SET NULL'], Literal['CASCADE']]
                   ) = None,
    ) -> _ForeignKey:
        ...

    def TIMESTAMP(self, *, timezone: Literal[True]
                  ) -> DbType[cg_dt_utils.DatetimeWithTimezone]:
        ...

    def Table(self, name: str, *args: T) -> RawTable:
        ...

    @t.overload
    def Enum(self, typ: t.Type[E], native_enum: bool = True) -> DbType[E]:
        ...

    @t.overload
    def Enum(self, *typ: T, name: str, native_enum: bool = True) -> DbType[T]:
        ...

    def Enum(self, *args: t.Any, **kwargs: t.Any) -> DbType[t.Any]:
        ...

    @t.overload
    def Column(
        self,
        name: str,
        type_: DbType[T],
        _fk: t.Optional[_ForeignKey] = None,
        *,
        unique: bool = False,
        nullable: Literal[True] = True,
        default: t.Union[T, t.Callable[[], T], None] = None,
        index: bool = False
    ) -> 'ColumnProxy[t.Optional[T]]':
        ...

    @t.overload
    def Column(
        self,
        name: str,
        type_: DbType[T],
        *,
        unique: bool = False,
        primary_key: Literal[True],
        default: t.Callable[[], T] = ...,
        index: bool = False
    ) -> 'ColumnProxy[T]':
        ...

    @t.overload
    def Column(
        self,
        name: str,
        type_: DbType[T],
        _fk: t.Optional[_ForeignKey] = None,
        *,
        unique: bool = False,
        nullable: Literal[False],
        default: t.Union[T, t.Callable[[], T]] = ...,
        **rest: t.Any
    ) -> 'ColumnProxy[T]':
        ...

    @t.overload  # NOQA
    def Column(
        self,
        type_: DbType[T],
        _fk: t.Optional[_ForeignKey] = None,
        *,
        nullable: Literal[False],
        default: t.Union[T, t.Callable[[], T]] = ...,
        **rest: t.Any
    ) -> 'ColumnProxy[T]':
        ...

    @t.overload  # NOQA
    def Column(
        self,
        type_: DbType[T],
        _fk: t.Optional[_ForeignKey] = None,
        *,
        unique: bool = False,
        nullable: Literal[True] = True,
        default: t.Union[T, t.Callable[[], T], None] = None,
        **rest: t.Any
    ) -> 'ColumnProxy[t.Optional[T]]':
        ...

    def Column(self, *args: t.Any, **kwargs: t.Any) -> t.Any:  # NOQA
        ...

    def PrimaryKeyConstraint(self, *args: t.Any) -> t.Any:
        ...

    def CheckConstraint(
        self, *args: t.Any, name: t.Optional[str] = None
    ) -> t.Any:
        ...

    def UniqueConstraint(
        self, *args: t.Any, name: t.Optional[str] = None
    ) -> t.Any:
        ...

    @t.overload
    def relationship(
        self,
        name: Union[t.Callable[[], t.Type[T]], t.Type[T]],
        *args: t.Any,
        foreign_keys: Union[_CP[Opt[int]], _CP[Opt[str]], _CP[Opt[UUID]]],
        **kwargs: t.Any,
    ) -> 'ColumnProxy[t.Optional[T]]':
        ...

    @t.overload  # NOQA
    def relationship(
        self,
        name: Union[t.Callable[[], t.Type[T]], t.Type[T]],
        *args: t.Any,
        foreign_keys: Union[_CP[int], _CP[UUID], _CP[str]],
        innerjoin: Literal[True] = None,
        **kwargs: t.Any,
    ) -> 'ColumnProxy[T]':
        ...

    @t.overload
    def relationship(
        self,
        name: Union[t.Callable[[], t.Type[T]], t.Type[T]],
        *,
        back_populates: str,
        cascade: str = '',
        uselist: Literal[True] = True,
        innerjoin: bool = None,
    ) -> 'ColumnProxy[t.List[T]]':
        ...

    @t.overload
    def relationship(
        self,
        name: Union[t.Callable[[], t.Type[T]], t.Type[T]],
        *,
        innerjoin: Literal[True],
        uselist: Literal[False],
        back_populates: str,
        cascade: str = '',
        lazy: Literal['select', 'join', 'selectin'] = 'select',
    ) -> 'ColumnProxy[T]':
        ...

    @t.overload
    def relationship(
        self,
        name: Union[t.Callable[[], t.Type[T]], t.Type[T]],
        *,
        uselist: Literal[False],
        back_populates: str,
        cascade: str = '',
        innerjoin: Literal[False] = False,
        lazy: Literal['select', 'join', 'selectin'] = 'select',
    ) -> 'ColumnProxy[Opt[T]]':
        ...

    @t.overload
    def relationship(
        self,
        name: Union[t.Callable[[], t.Type[T]], t.Type[T]],
        *,
        remote_side: t.List[ColumnProxy[t.Any]],
        backref: _Backref,
    ) -> 'ColumnProxy[Opt[T]]':
        ...

    @t.overload
    def relationship(
        self,
        name: Union[t.Callable[[], t.Type[T]], t.Type[T]],
        *,
        backref: _Backref,
        uselist: Literal[True],
        lazy: Literal['select', 'join', 'selectin'] = 'select',
    ) -> 'ColumnProxy[t.List[T]]':
        ...

    @t.overload  # NOQA
    def relationship(
        self,
        name: Union[t.Callable[[], t.Type[T]], t.Type[T]],
        *,
        uselist: Literal[True],
        cascade: str = '',
        back_populates: str = None,
        backref: _Backref = None,
        order_by: t.Union[t.Callable[[], 'DbColumn'], t.
                          Callable[[], 'ColumnOrder']] = None,
        lazy: Literal['select', 'joined', 'selectin'] = 'select',
    ) -> 'ColumnProxy[t.List[T]]':
        ...

    @t.overload  # NOQA
    def relationship(
        self,
        name: t.Callable[[], t.Type[_T_BASE]],
        *,
        uselist: Literal[True],
        secondary: 'RawTable',
        cascade: str = '',
        lazy: Literal['select', 'join', 'selectin'] = 'select',
        order_by: t.Union[t.Callable[[], 'DbColumn'], t.
                          Callable[[], 'ColumnOrder']] = None,
    ) -> 'ColumnProxy[t.List[_T_BASE]]':
        ...

    @t.overload  # NOQA
    def relationship(
        self,
        name: str,
        *,
        backref: _Backref = None,
        collection_class: object,
        secondary: 'RawTable' = None,
        cascade: str = '',
    ) -> t.Any:
        ...

    def relationship(self, *args: t.Any, **kwargs: t.Any) -> t.Any:  # NOQA
        ...

    def backref(self, name: str, *args: t.Any, **kwargs: t.Any) -> _Backref:
        ...


class ColumnOrder:
    ...


class DbColumn(t.Generic[T]):  # pragma: no cover
    '''This class is used for type checking only.

    It has no implementation and instantiating an instance raises an error.
    '''

    def __init__(self) -> None:
        raise ValueError

    def any(self, cond: 'DbColumn[bool]' = None) -> 'DbColumn[bool]':
        ...

    def in_(
        self, val: t.Union[t.Iterable[T], 'DbColumn[T]',
                           'MyNonOrderableQuery[T]', 'RawTable']
    ) -> 'DbColumn[bool]':
        ...

    def isnot(self, val: t.Optional[T]) -> 'DbColumn[bool]':
        ...

    def label(self, name: str) -> 'DbColumn[T]':
        ...

    def is_(self, val: T) -> 'DbColumn[bool]':
        ...

    def __invert__(self: 'DbColumn[bool]') -> 'DbColumn[bool]':
        ...

    def desc(self) -> ColumnOrder:
        ...

    def asc(self) -> ColumnOrder:
        ...

    @t.overload
    def has(self: 'DbColumn[t.List[Y]]', __arg: Y) -> 'DbColumn[bool]':
        ...

    @t.overload
    def has(self, **kwargs: object) -> 'DbColumn[bool]':
        ...

    def has(self, *args: object, **kwargs: object) -> t.Any:
        ...

    def __eq__(  # type: ignore
        self, other: Union[t.Optional[T], 'DbColumn[T]', 'DbColumn[t.Optional[T]]',
                           'MyNonOrderableQuery[T]']
    ) -> 'DbColumn[bool]':
        ...

    def __ne__(  # type: ignore
        self, other: Union[t.Optional[T], 'DbColumn[T]', 'DbColumn[t.Optional[T]]',
                           'MyNonOrderableQuery[T]']
    ) -> 'DbColumn[bool]':
        ...

    def __ge__(
        self, other: t.Union[T, 'DbColumn[T]', 'DbColumn[t.Optional[T]]']
    ) -> 'DbColumn[bool]':
        ...

    def __lt__(
        self, other: t.Union[T, 'DbColumn[T]', 'DbColumn[t.Optional[T]]']
    ) -> 'DbColumn[bool]':
        ...

    def __or__(self, other: 'DbColumn[bool]') -> 'DbColumn[bool]':
        ...


class Mapper(t.Generic[_T_BASE]):
    @property
    def polymorphic_map(self) -> t.Dict[object, 'Mapper[_T_BASE]']:
        ...

    @property
    def class_(self) -> _T_BASE:
        ...


class Base:  # pragma: no cover
    query = None  # type: t.ClassVar[t.Any]

    def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
        pass


class MyNonOrderableQuery(t.Generic[T], t.Iterable):  # pragma: no cover
    delete: t.Callable[[QuerySelf], None]
    subquery: t.Callable[[QuerySelf, str], RawTable]
    limit: t.Callable[[QuerySelf, int], QuerySelf]
    first: t.Callable[[QuerySelf], t.Optional[T]]
    exists: t.Callable[[QuerySelf], DbColumn[bool]]
    count: t.Callable[[QuerySelf], int]
    one: t.Callable[[QuerySelf], T]
    __iter__: t.Callable[[QuerySelf], t.Iterator[T]]

    def distinct(self: QuerySelf, on: t.Any = None) -> 'QuerySelf':
        pass

    def all(self) -> t.List[T]:
        ...

    def with_for_update(
        self: QuerySelf,
        *,
        read: bool = False,
        of: t.Optional[t.Type[Base]] = None,
    ) -> 'QuerySelf':
        ...

    def one_or_none(self) -> t.Optional[T]:
        ...

    def select_from(self: QuerySelf, other: t.Type[Base]) -> 'QuerySelf':
        ...

    def slice(self: QuerySelf, start: int, end: int) -> 'QuerySelf':
        ...

    def get(self, arg: t.Any) -> t.Optional[T]:
        ...

    def update(
        self,
        vals: t.Mapping[t.Union[str, DbColumn], t.Any],
        synchronize_session: t.Union[str, bool] = '__NOT_REAL__'
    ) -> None:
        ...

    def from_self(self, *args: t.Type[Z]) -> 'MyNonOrderableQuery[Z]':
        ...

    def join(
        self: QuerySelf,
        to_join: t.Union[t.Type['Base'], RawTable, 'DbColumn[_T_BASE]'],
        cond: 'DbColumn[bool]' = None,
        *,
        isouter: bool = False,
    ) -> QuerySelf:
        ...

    def filter(self: QuerySelf, *args: DbColumn[bool]) -> 'QuerySelf':
        ...

    def filter_by(
        self: QuerySelf, *args: t.Any, **kwargs: t.Any
    ) -> 'QuerySelf':
        ...

    def options(self: QuerySelf, *args: t.Any) -> 'QuerySelf':
        ...

    def having(self: QuerySelf, *args: t.Any) -> 'QuerySelf':
        ...

    def group_by(self: QuerySelf, arg: t.Any) -> 'QuerySelf':
        ...

    @t.overload
    def with_entities(self, __arg: DbColumn[Z]) -> 'MyQueryTuple[Z]':
        ...

    @t.overload
    def with_entities(
        self, __arg1: DbColumn[Z], __arg2: DbColumn[Y]
    ) -> 'MyQuery[t.Tuple[Z, Y]]':
        ...

    @t.overload
    def with_entities(
        self, __arg1: DbColumn[Z], __arg2: DbColumn[Y], __arg3: DbColumn[U]
    ) -> 'MyQuery[t.Tuple[Z, Y,U]]':
        ...

    def with_entities(self, *args: t.Any) -> 'MyQuery[t.Any]':
        ...


class MyQuery(t.Generic[T], MyNonOrderableQuery[T]):
    def order_by(
        self: QuerySelf, *args: t.Union[DbColumn, ColumnOrder]
    ) -> 'QuerySelf':
        ...

    def from_self(self, *args: t.Type[Z]) -> 'MyQuery[Z]':
        ...


class MyQueryTuple(t.Generic[T], MyQuery[t.Tuple[T]]):
    def as_scalar(self) -> 'MyQuery[T]':
        ...

    def scalar(self) -> t.Optional[T]:
        ...

    def label(self, name: str) -> 'DbColumn[T]':
        ...


_MyQuery = MyQuery

if t.TYPE_CHECKING:

    @t.overload
    def hybrid_property(fget: t.Callable[[Z], T], ) -> ImmutableColumnProxy[T]:
        ...

    @t.overload
    def hybrid_property(
        fget: t.Callable[[Z], T],
        fset: t.Callable[[Z, Y], None],
        fdel: None = None,
        expr: t.Callable[[t.Type[Z]], 'DbColumn[T]'] = None,
    ) -> MutableColumnProxy[T, Y]:
        ...

    def hybrid_property(*args: object, **kwargs: object) -> t.Any:
        ...

    hybrid_expression = staticmethod
else:
    from sqlalchemy.ext.hybrid import hybrid_property
    def hybrid_expression(fun: T) -> T:
        return fun
