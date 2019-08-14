# SPDX-License-Identifier: AGPL-3.0-only
import io
import os
import json
import uuid
import datetime
from copy import deepcopy

import pytest
from werkzeug.local import LocalProxy

import psef.models as m
from psef.permissions import CoursePermission as CPerm


def get_id(obj):
    if isinstance(obj, dict):
        return obj['id']
    elif isinstance(obj, int):
        return obj
    else:
        return obj.id


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


def create_course(test_client):
    name = f'__NEW_COURSE__-{uuid.uuid4()}'
    return test_client.req(
        'post',
        '/api/v1/courses/',
        200,
        data={'name': name},
        result={'name': name, '__allow_extra__': True},
    )


def create_assignment(
    test_client, course_id=None, state='hidden', deadline=None
):
    name = f'__NEW_ASSIGNMENT__-{uuid.uuid4()}'
    if course_id is None:
        course_id = create_course(test_client)

    res = test_client.req(
        'post',
        f'/api/v1/courses/{get_id(course_id)}/assignments/',
        200,
        data={'name': name},
        result={'name': name, '__allow_extra__': True},
    )
    data = {}
    if state != 'hidden':
        data['state'] = state
    if deadline is not None:
        if isinstance(deadline, datetime.datetime):
            deadline = deadline.isoformat()
        data['deadline'] = deadline
    res = test_client.req(
        'patch', f'/api/v1/assignments/{res["id"]}', 200, data=data
    )
    return res


def create_submission(
    test_client,
    assignment_id=None,
    err=None,
    submission_data=(
        (
            f'{os.path.dirname(__file__)}/../test_data/test_submissions/'
            'multiple_dir_archive.zip'
        ),
        'f.zip',
    )
):
    status = err or 201
    err_t = create_error_template()
    err_t['__allow_extra__'] = True
    if assignment_id is None:
        assignment_id = create_assignment(test_client)['id']
    result = ({
        'id': int,
        'user': dict,
        'created_at': str,
        'assignee': None,
        'grade': None,
        'comment': None,
        'comment_author': None,
        'grade_overridden': False,
    } if err is None else err_t)

    return test_client.req(
        'post',
        f'/api/v1/assignments/{assignment_id}/submission',
        status,
        real_data={'file': submission_data},
        result=result,
    )


def create_group_set(
    test_client, course_id, min_size, max_size, assig_ids=None
):
    if assig_ids is None:
        assig_ids = []
    g_set = test_client.req(
        'put',
        f'/api/v1/courses/{course_id}/group_sets/',
        data={'minimum_size': min_size, 'maximum_size': max_size},
        status_code=200,
        result={
            'id': int,
            'maximum_size': max_size,
            'minimum_size': min_size,
            'assignment_ids': [],
        },
    )
    for assig_id in assig_ids:
        test_client.req(
            'patch',
            f'/api/v1/assignments/{assig_id}',
            200,
            data={'group_set_id': g_set['id']},
        )
    return g_set


def create_user_with_role(session, role, courses, name=None):
    if not isinstance(courses, list):
        courses = [courses]
    n_id = str(uuid.uuid4())
    new_role = m.Role(name=f'NEW_ROLE--{n_id}')
    user = m.User(
        name=f'NEW_USER-{n_id}' if name is None else name,
        email=f'new_user-{n_id}@a.nl',
        password=n_id,
        active=True,
        username=f'a-the-a-er-{n_id}' if name is None else f'{name}{n_id}',
        role=new_role,
    )
    for course in courses:
        user.courses[get_id(course)] = m.CourseRole.query.filter_by(
            name=role, course_id=get_id(course)
        ).one()
    session.add(user)
    session.commit()
    u_id = user.id
    return LocalProxy(lambda: m.User.query.get(u_id))


def create_user_with_perms(session, perms, courses, name=None):
    role_name = f'NEW-COURSE-ROLE-{uuid.uuid4().hex}'
    courses = courses if isinstance(courses, list) else [courses]
    for course in courses:
        if isinstance(course, dict):
            course = m.Course.query.get(course['id'])
        crole = m.CourseRole(name=role_name, course=course)
        for perm in CPerm:
            crole.set_permission(perm, perm in perms)
        session.add(crole)
    session.flush()
    user = create_user_with_role(session, role_name, courses, name)
    print('Created user', user.id, 'with permissions:', perms)
    return user


def create_group(test_client, group_set_id, member_ids):
    return test_client.req(
        'post',
        f'/api/v1/group_sets/{group_set_id}/group',
        data={'member_ids': member_ids},
        status_code=200,
        result={'id': int, 'name': str, 'members': list},
    )


def create_error_template():
    return {'code': str, 'message': str, 'description': str}


def get_newest_submissions(test_client, assignment):
    # When duplicate keys occur last wins in dict comprehensions so
    # this makes sure we only have the latest submission for a user.
    return {
        s['user']['id']: s
        for s in reversed(
            test_client.req(
                'get',
                f'/api/v1/assignments/{get_id(assignment)}/submissions/', 200
            )
        )
    }


def get_simple_rubric():
    return {
        'rows': [{
            'header': 'My header',
            'description': 'My description',
            'items': [
                {
                    'description': 'item description',
                    'header': 'header',
                    'points': 4,
                },
                {
                    'description': 'item description',
                    'header': 'header',
                    'points': 5,
                },
            ],
        }]
    }


def get_auto_test_io_step():
    return {
        'type': 'io_test',
        'data': {
            'inputs': [
                {
                    'name': 'without name',
                    'weight': 0.5,
                    'args': '',
                    'stdin': '',
                    'output': 'hello stranger!',
                    'options': [],
                },
                {
                    'name': 'with name',
                    'weight': 0.5,
                    'args': 'Thomas',
                    'stdin': '',
                    'output': 'hello Thomas',
                    'options': ['substring'],
                },
            ],
            'program': 'python3 test.py',
        },
        'name': 'Simple io test',
        'hidden': False,
        'weight': 1,
    }


def get_auto_test_custom_output_step():
    return {
        'type': 'custom_output',
        'data': {'program': 'echo 1', 'regex': '\\f'},
        'name': 'Custom output',
        'weight': 1,
        'hidden': False,
    }


def get_auto_test_check_points_step():
    return {
        'type': 'check_points',
        'data': {'min_points': 0.5},
        'name': 'Check points',
        'weight': 0,
        'hidden': False,
    }


def get_auto_test_run_program_step(sleep_time=5):
    return {
        'type': 'run_program',
        'data': {'program': f'sleep {sleep_time}'},
        'name': 'Simple run program',
        'weight': 1,
        'hidden': False,
    }


def create_auto_test(
    test_client,
    assignment,
    amount_sets=1,
    amount_suites=1,
    stop_points=None,
    grade_calculation=None,
    amount_fixtures=0,
):
    a_id = get_id(assignment)

    test = test_client.req(
        'post',
        '/api/v1/auto_tests/',
        data={'assignment_id': a_id, 'setup_script': 'ls'},
        status_code=200,
        result={
            'id': int,
            'fixtures': [],
            'setup_script': 'ls',
            'run_setup_script': '',
            'finalize_script': '',
            'sets': [],
            'assignment_id': a_id,
            'runs': [],
            'grade_calculation': None,
        },
    )

    if grade_calculation is not None:
        test_client.req(
            'patch',
            f'/api/v1/auto_tests/{get_id(test)}',
            200,
            data={'grade_calculation': grade_calculation},
            result={
                'grade_calculation': grade_calculation, '__allow_extra__': True
            }
        )

    def get_test():
        t_id = get_id(test)
        return test_client.req('get', f'/api/v1/auto_tests/{t_id}', 200)

    if amount_sets * amount_suites > 0:
        rubric_data = get_simple_rubric()
        rubric_data['rows'] = [
            deepcopy(rubric_data['rows'][0])
            for _ in range(amount_suites * amount_sets)
        ]

        rubric = test_client.req(
            'put',
            f'/api/v1/assignments/{a_id}/rubrics/',
            200,
            data=rubric_data
        )

    for idx1 in range(amount_sets):
        s = test_client.req(
            'post', f'/api/v1/auto_tests/{get_id(test)}/sets/', 200
        )

        if stop_points is not None and stop_points[idx1] is not None:
            test_client.req(
                'patch',
                f'/api/v1/auto_tests/{get_id(test)}/sets/{get_id(s)}',
                200,
                data={'stop_points': stop_points[idx1]}
            )

        for idx2 in range(amount_suites):
            rubric_index = idx1 * amount_suites + idx2

            test_client.req(
                'patch',
                f'/api/v1/auto_tests/{get_id(test)}/sets/{get_id(s)}/suites/',
                200,
                data={
                    'steps': [
                        get_auto_test_io_step(),
                        get_auto_test_check_points_step(),
                        get_auto_test_custom_output_step(),
                        get_auto_test_run_program_step(5 if idx1 else 0),
                    ],
                    'rubric_row_id': rubric[rubric_index]['id'],
                    'network_disabled': bool(idx2),
                },
            )

    for i in range(amount_fixtures):
        test_client.req(
            'patch',
            f'/api/v1/auto_tests/{get_id(test)}',
            200,
            real_data={
                'json': (
                    io.BytesIO(
                        json.dumps({
                            'has_new_fixtures': True,
                        }).encode()
                    ), 'json'
                ),
                'fixture': (io.BytesIO(f'hello{i}'.encode()), 'fixture1'),
            }
        )

    return get_test()
