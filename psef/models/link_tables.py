"""This module defines all link tables.

SPDX-License-Identifier: AGPL-3.0-only
"""

from cg_sqlalchemy_helpers.types import RawTable

from . import db

roles_permissions: RawTable = db.Table(  # pylint: disable=invalid-name
    'roles-permissions',
    db.Column(
        'permission_id', db.Integer,
        db.ForeignKey('Permission.id', ondelete='CASCADE')
    ),
    db.Column(
        'role_id', db.Integer, db.ForeignKey('Role.id', ondelete='CASCADE')
    )
)

course_permissions: RawTable = db.Table(  # pylint: disable=invalid-name
    'course_roles-permissions',
    db.Column(
        'permission_id', db.Integer,
        db.ForeignKey('Permission.id', ondelete='CASCADE')
    ),
    db.Column(
        'course_role_id', db.Integer,
        db.ForeignKey('Course_Role.id', ondelete='CASCADE')
    )
)

user_course: RawTable = db.Table(  # pylint: disable=invalid-name
    'users-courses',
    db.Column(
        'course_id', db.Integer,
        db.ForeignKey('Course_Role.id', ondelete='CASCADE')
    ),
    db.Column(
        'user_id', db.Integer, db.ForeignKey('User.id', ondelete='CASCADE')
    )
)

work_rubric_item: RawTable = db.Table(  # pylint: disable=invalid-name
    'work_rubric_item',
    db.Column(
        'work_id', db.Integer, db.ForeignKey('Work.id', ondelete='CASCADE')
    ),
    db.Column(
        'rubricitem_id', db.Integer,
        db.ForeignKey('RubricItem.id', ondelete='CASCADE')
    )
)

users_groups: RawTable = db.Table(  # pylint: disable=invalid-name
    'users-groups',
    db.Column(
        'group_id', db.Integer,
        db.ForeignKey('Group.id', ondelete='CASCADE')
    ),
    db.Column(
        'user_id', db.Integer, db.ForeignKey('User.id', ondelete='CASCADE')
    )
)
