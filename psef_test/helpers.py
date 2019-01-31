# SPDX-License-Identifier: AGPL-3.0-only
import os
import uuid

import pytest
from werkzeug.local import LocalProxy

import psef.models as m
from psef.permissions import CoursePermission as CPerm


def create_marker(marker):
    def outer(*vals, **kwargs):
        def inner(vals):
            if vals is not None and isinstance(vals, tuple):
                return pytest.param(*vals, marks=marker(**kwargs))
            else:
                return pytest.param(vals, marks=marker(**kwargs))

        if kwargs:
            return inner
        return inner(*vals)

    return outer


def create_submission(test_client, assignment_id, err=None):
    status = err or 201
    err_t = create_error_template()
    err_t['__allow_extra__'] = True
    result = {
        'id': int,
        'user': dict,
        'created_at': str,
        'assignee': None,
        'grade': None,
        'comment': None,
        'comment_author': None,
    } if err is None else err_t

    return test_client.req(
        'post',
        f'/api/v1/assignments/{assignment_id}/submission',
        status,
        real_data={
            'file':
                (
                    f'{os.path.dirname(__file__)}/../test_data/'
                    'test_submissions/multiple_dir_archive.zip', 'f.zip'
                )
        },
        result=result
    )


def create_group_set(
    test_client, course_id, min_size, max_size, assig_ids=None
):
    if assig_ids is None:
        assig_ids = []
    g_set = test_client.req(
        'put',
        f'/api/v1/courses/{course_id}/group_sets/',
        data={
            'minimum_size': min_size,
            'maximum_size': max_size,
        },
        status_code=200,
        result={
            'id': int,
            'maximum_size': max_size,
            'minimum_size': min_size,
            'assignment_ids': [],
        }
    )
    for assig_id in assig_ids:
        test_client.req(
            'patch',
            f'/api/v1/assignments/{assig_id}',
            200,
            data={'group_set_id': g_set['id']}
        )
    return g_set


def create_user_with_perms(session, perms, course):
    n_id = str(uuid.uuid4())
    new_role = m.Role(name=f'NEW_ROLE--{n_id}')
    user = m.User(
        name=f'NEW_USER-{n_id}',
        email=f'new_user-{n_id}@a.nl',
        password=n_id,
        active=True,
        username=f'a-the-a-er-{n_id}',
        role=new_role,
    )
    crole = m.CourseRole(name=f'NEW-COURSE-ROLE-{n_id}', course=course)
    for perm in CPerm:
        crole.set_permission(perm, perm in perms)
    user.courses[course.id] = crole
    session.add(crole)
    session.add(user)
    session.commit()
    u_id = user.id
    print('Created user', u_id, 'with permissions:', perms)
    return LocalProxy(lambda: m.User.query.get(u_id))


def create_group(test_client, group_set_id, member_ids):
    return test_client.req(
        'post',
        f'/api/v1/group_sets/{group_set_id}/group',
        data={'member_ids': member_ids},
        status_code=200,
        result={
            'id': int,
            'name': str,
            'members': list,
        }
    )


def create_error_template():
    return {
        'code': str,
        'message': str,
        'description': str,
    }
