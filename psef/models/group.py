"""This module defines all models needed for groups.

SPDX-License-Identifier: AGPL-3.0-only
"""
import typing as t
import datetime
from sys import maxsize as _maxsize

import coolname
from sqlalchemy.sql.expression import or_ as sql_or
from sqlalchemy.sql.expression import func as sql_func

from cg_sqlalchemy_helpers.types import MyQueryTuple

from . import Base, DbColumn, db
from . import user as user_models
from . import work as work_models
from . import _MyQuery
from . import assignment as assignment_models
from ..helpers import NotEqualMixin
from ..exceptions import APICodes, APIException
from .link_tables import users_groups

if t.TYPE_CHECKING:  # pragma: no cover
    # pylint: disable=invalid-name,unused-import
    from . import course as course_models
    from . import assignment as assignment_models
    cached_property = property
else:
    from werkzeug.utils import cached_property


class GroupSet(NotEqualMixin, Base):
    """This class represents a group set.

    A group set is a single wrapper over all groups. Every group is part of a
    group set. The group set itself is connected to a single course and zero or
    more assignments in this course.

    :ivar minimum_size: The minimum size of that group should have before it
        can be used to submit a submission.
    :ivar maximum_size: The maximum amount of members a group can ever have.
    """
    if t.TYPE_CHECKING:  # pragma: no cover
        query: t.ClassVar[_MyQuery['GroupSet']]
    __tablename__ = 'GroupSet'

    id: int = db.Column('id', db.Integer, primary_key=True)
    minimum_size: int = db.Column('minimum_size', db.Integer, nullable=False)
    maximum_size: int = db.Column('maximum_size', db.Integer, nullable=False)
    course_id: int = db.Column(
        'Course_id', db.Integer, db.ForeignKey('Course.id'), nullable=False
    )
    created_at: datetime.datetime = db.Column(
        db.DateTime, default=datetime.datetime.utcnow
    )

    course: 'course_models.Course' = db.relationship(
        'Course',
        foreign_keys=course_id,
        back_populates='group_sets',
        innerjoin=True,
    )

    assignments = db.relationship(
        'Assignment',
        back_populates='group_set',
        lazy='joined',
        uselist=True,
        order_by='Assignment.created_at'
    )  # type: t.MutableSequence['assignment_models.Assignment']

    groups = db.relationship(
        'Group',
        back_populates='group_set',
        lazy='select',
        cascade='all,delete',
        uselist=True,
        order_by='Group.created_at',
    )  # type: t.MutableSequence['Group']

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, GroupSet):
            return NotImplemented
        return self.id == other.id

    def get_valid_group_for_user(self, user: 'user_models.User'
                                 ) -> t.Optional['Group']:
        """Get the group for the given user.

        :param user: The user to get the group for.
        :returns: A group if a valid group was found, or ``None`` if no group
            is needed to submit to an assignment connected to this group set.
        :raises APIException: If the amount of members of the found group is
            less than the minimum size of this group set.
        """
        group = db.session.query(Group).filter_by(group_set_id=self.id).filter(
            t.cast(
                DbColumn[t.List['user_models.User']],
                Group.members,
            ).any(user_models.User.id == user.id)
        ).first()

        if group is None:
            if self.minimum_size > 1:
                raise APIException(
                    'No group was found',
                    (
                        f'The user {user.id} is not in a group of at least'
                        f' {self.minimum_size} people'
                    ),
                    APICodes.INSUFFICIENT_GROUP_SIZE,
                    404,
                    group=None,
                )
            else:
                return None
        elif len(group.members) < self.minimum_size:
            raise APIException(
                "Group doesn't have enough members",
                (
                    f"The group {group.id} doesn't have at least"
                    f' {self.minimum_size} members'
                ),
                APICodes.INSUFFICIENT_GROUP_SIZE,
                400,
                group=group,
            )
        else:
            return group

    __table_args__ = (
        db.CheckConstraint('minimum_size <= maximum_size'),
        db.CheckConstraint('minimum_size > 0')
    )

    def __to_json__(self) -> t.Mapping[str, t.Union[int, t.List[int]]]:
        own_assignments = set(a.id for a in self.assignments)
        visible_assigs = [
            a.id for a in self.course.get_all_visible_assignments()
            if a.id in own_assignments
        ]
        return {
            'id': self.id,
            'minimum_size': self.minimum_size,
            'maximum_size': self.maximum_size,
            'assignment_ids': visible_assigs,
        }

    def __get_group_size_query(self, asc: bool,
                               has_subs: bool) -> MyQueryTuple[int]:
        count = sql_func.count(users_groups.c.user_id)
        res = db.session.query(count).group_by(users_groups.c.group_id).join(
            Group,
            Group.id == users_groups.c.group_id,
        ).filter(
            Group.group_set_id == self.id,
        ).order_by(count if asc else count.desc())
        if has_subs:
            res = res.filter(
                work_models.Work.query.filter_by(
                    user_id=Group.virtual_user_id
                ).exists()
            )
        return res

    @cached_property
    def largest_group_size(self) -> int:
        """Get the size of the largest group in this group set.

        This group doesn't have to have submission.

        .. note::

            This property is cached within a request, and won't update after
            adding groups.

        :returns: The size of the largest group in the group set. The value -1
            is returned if there are no groups in this group set.
        """
        return self.__get_group_size_query(
            asc=False, has_subs=False
        ).limit(1).scalar() or -1

    @cached_property
    def smallest_group_size(self) -> int:
        """Get the size of the smallest group in this group set.

        .. note:: Only groups with a submission are counted.

        .. note::

            This property is cached within a request, and won't update after
            adding groups.

        :returns: The size of the smallest group with a submission in the group
            set. The value :class:`.sys.maxsize` is returned if there are no
            groups with a submission in this group set.
        """
        return self.__get_group_size_query(
            asc=False, has_subs=True
        ).limit(1).scalar() or _maxsize


class Group(Base):
    """This class represents a single group.

    A group is a collection of real (non virtual) users that itself is
    connected to a virtual user. A group is connected to a :class:`.GroupSet`.

    :ivar ~.Group.name: The name of the group. This has to be unique in a group
        set.
    :ivar virtual_user: The virtual user this group is connected to. This user
        is used to submissions as the group.
    :ivar group_set: The :class:`.GroupSet` this group is connected to.
    """
    if t.TYPE_CHECKING:  # pragma: no cover
        query: t.ClassVar[_MyQuery['Group']]
    __tablename__ = 'Group'

    id: int = db.Column('id', db.Integer, primary_key=True)
    name: str = db.Column('name', db.Unicode)
    group_set_id: int = db.Column(
        'group_set_id',
        db.Integer,
        db.ForeignKey('GroupSet.id'),
        nullable=False,
    )
    created_at: datetime.datetime = db.Column(
        db.DateTime, default=datetime.datetime.utcnow
    )
    virtual_user_id: int = db.Column(
        'virtual_user_id',
        db.Integer,
        db.ForeignKey('User.id'),
        nullable=False,
    )
    members: t.MutableSequence['user_models.User'] = db.relationship(
        'User',
        secondary=users_groups,
        lazy='selectin',
        order_by='User.name',
    )
    virtual_user: 'user_models.User' = db.relationship(
        'User', foreign_keys=virtual_user_id
    )

    group_set: GroupSet = db.relationship('GroupSet', back_populates='groups')

    __table_args__ = (db.UniqueConstraint('group_set_id', 'name'), )

    @cached_property
    def has_a_submission(self) -> bool:
        """Is a submission handed in by this group.

        .. note::

            This property is cached after the first access within a request.

        """
        return db.session.query(
            work_models.Work.query.filter_by(user_id=self.virtual_user_id
                                             ).exists()
        ).scalar()

    @classmethod
    def create_group(
        cls: 't.Type[Group]',
        group_set: GroupSet,
        members: t.MutableSequence['user_models.User'],
        name: t.Optional[str] = None,
    ) -> 'Group':
        """Create a group with the given members.

        .. warning::

           This function **does** check if the given members are not yet in a
           group. It however doesn't check if the current user has the
           permission to add these users to the group, nor if the members are
           enrolled in the course.

        :param group_set: In which group set should this group be placed.
        :param members: The initial members should this group have.
        :param name: The name of the group. If not given a random name is
            generated.
        :returns: The newly created group.
        """
        if members and db.session.query(
            cls.contains_users(members).filter_by(group_set=group_set).exists()
        ).scalar():
            raise APIException(
                'Member already in a group',
                'One of the members is already in a group for this group set',
                APICodes.INVALID_PARAM, 400
            )
        virt = user_models.User.create_virtual_user('GROUP_')
        name = name or ' '.join(coolname.generate(3))
        self = cls(
            group_set=group_set, members=members, virtual_user=virt, name=name
        )
        db.session.flush()
        virt.name += str(self.id)
        return self

    @classmethod
    def contains_users(
        cls: t.Type['Group'],
        users: t.Sequence['user_models.User'],
        *,
        include_empty: bool = False,
    ) -> _MyQuery['Group']:
        """Get a query that for all groups that include the given users.

        :param users: Filter groups so that at least one of their members is
            one of these users.
        :param include_empty: Also include empty groups, so without users, in
            the query.
        :returns: The query as described above.
        """
        res = db.session.query(Group)
        cond = t.cast(DbColumn[int], Group.id).in_(
            db.session.query(users_groups.c.group_id).filter(
                t.cast(DbColumn[int],
                       users_groups.c.user_id).in_([m.id for m in users])
            )
        )
        if include_empty:
            cond = sql_or(cond, ~t.cast(DbColumn[object], Group.members).any())

        return res.filter(cond)

    def get_member_lti_states(
        self,
        assignment: 'assignment_models.Assignment',
    ) -> t.Mapping[int, bool]:
        """Get the lti state of all members in the group.

        Check if it is possible to passback the grade for all members in this
        group. This is done by checking if there is a row for each user,
        assignment combination in the `.assignment_models.AssignmentResult`
        table.

        :param assignment: The assignment to get the states for.
        :returns: A mapping between user id and if we can passback the grade
            for this user for every member in this group.
        """
        assert assignment.id in {a.id for a in self.group_set.assignments}

        if assignment.is_lti and self.members:
            assig_results: t.Set[int] = set(
                user_id for user_id, in db.session.query(
                    assignment_models.AssignmentResult
                ).filter_by(assignment_id=assignment.id).filter(
                    t.cast(
                        DbColumn[int],
                        user_models.User.id,
                    ).in_([member.id for member in self.members])
                ).with_entities(
                    t.cast(
                        DbColumn[int],
                        assignment_models.AssignmentResult.user_id,
                    )
                )
            )
            return {
                member.id: member.id in assig_results
                for member in self.members
            }
        else:
            return {member.id: True for member in self.members}

    def __to_json__(self) -> t.Mapping[str, t.Any]:
        return {
            'id': self.id,
            'members': self.members,
            'name': self.name,
        }
