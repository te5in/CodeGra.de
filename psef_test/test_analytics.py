import pytest

import psef
import helpers
import psef.models as m
from helpers import get_id
from test_feedback import mail_functions, make_add_reply

RUBRIC = {
    'rows': [{
        'header': 'My header',
        'description': 'My description',
        'items': [{
            'description': '5points',
            'header': 'bladie',
            'points': 5
        }, {
            'description': '10points',
            'header': 'bladie',
            'points': 10,
        }]
    }, {
        'header': 'My header2',
        'description': 'My description2',
        'items': [{
            'description': '1points',
            'header': 'bladie',
            'points': 1
        }, {
            'description': '2points',
            'header': 'bladie',
            'points': 2,
        }]
    }, {
        'header': 'Compensation',
        'description': 'WOW',
        'items': [{
            'description': 'BLA',
            'header': 'Never selected',
            'points': -1,
        }, {
            'description': 'BLA+',
            'header': 'Never selected 2',
            'points': 0,
        }],
    }]
}  # yapf: disable


def get_rubric_item(rubric, head, desc):
    for row in rubric:
        if row['header'] == head:
            for item in row['items']:
                if item['description'] == desc:
                    return item


def test_get_entire_workspace(
    logged_in, test_client, session, admin_user, describe, tomorrow
):
    with describe('setup'), logged_in(admin_user):
        assignment = helpers.create_assignment(
            test_client, state='open', deadline=tomorrow
        )
        course = assignment['course']
        teacher = admin_user
        student = helpers.create_user_with_role(session, 'Student', course)
        w_id, = assignment["analytics_workspace_ids"]

        work_id = helpers.get_id(
            helpers.create_submission(
                test_client, assignment, for_user=student
            )
        )

        url = f'/api/v1/analytics/{w_id}'

        rubric = test_client.req(
            'put',
            f'/api/v1/assignments/{get_id(assignment)}/rubrics/',
            200,
            data=RUBRIC
        )

        def test(*args):
            if not isinstance(args[0], tuple):
                args = [(student, work_id, *args)]

            test_client.req(
                'get',
                url,
                200,
                result={
                    'id': w_id,
                    'assignment_id': assignment['id'],
                    'student_submissions': {
                        str(get_id(arg[0])): [{
                            'id': get_id(arg[1]),
                            'created_at': str,
                            'grade': arg[2],
                            'assignee_id': arg[3] and get_id(arg[3]),
                        }]
                        for arg in args
                    },
                    'data_sources': [str, str],
                }
            )

    with describe('should send the current grade'), logged_in(teacher):
        test(None, None)

        for item in [
            get_rubric_item(rubric, 'My header', '10points'),
            get_rubric_item(rubric, 'My header2', '2points'),
        ]:
            test_client.req(
                'patch',
                f'/api/v1/submissions/{work_id}/rubricitems/{item["id"]}',
                204,
            )

        test(10, None)

        test_client.req(
            'patch',
            f'/api/v1/submissions/{work_id}',
            200,
            data={'grade': 0.5}
        )
        test(0.5, None)

        test_client.req(
            'patch',
            f'/api/v1/submissions/{work_id}',
            200,
            data={'grade': None}
        )
        test(10, None)

    with describe('should show the assignee'), logged_in(teacher):
        test_client.req(
            'patch',
            f'/api/v1/submissions/{work_id}/grader',
            204,
            data={'user_id': get_id(teacher)}
        )

        test(10, teacher)

    with describe('should not show test students'), logged_in(teacher):
        helpers.create_submission(
            test_client, assignment, is_test_submission=True
        )

        test(10, teacher)

    with describe('Should show multiple students'), logged_in(teacher):
        student2 = helpers.create_user_with_role(session, 'Student', course)
        work2 = helpers.create_submission(
            test_client, assignment, for_user=student2
        )
        test((student, work_id, 10, teacher), (student2, work2, None, None))

    with describe('students cannot access it'), logged_in(student):
        test_client.req('get', url, 403)


def test_getting_inline_feedback_analytics(
    logged_in, test_client, session, admin_user, describe, tomorrow,
    make_add_reply
):
    with describe('setup'), logged_in(admin_user):
        assignment = helpers.create_assignment(
            test_client, state='open', deadline=tomorrow
        )
        course = assignment['course']
        teacher = admin_user
        student = helpers.create_user_with_role(session, 'Student', course)

        work_id = helpers.get_id(
            helpers.create_submission(
                test_client, assignment, for_user=student
            )
        )

        add_reply = make_add_reply(work_id)
        base_url = (
            f'/api/v1/analytics/{assignment["analytics_workspace_ids"][0]}'
        )
        url = base_url + '/data_sources/inline_feedback'

        def test(amount):
            test_client.req(
                'get',
                url,
                200,
                result={
                    'name': 'inline_feedback',
                    'data': {str(work_id): {'total_amount': amount, }},
                },
            )

    with describe('should be includes as data source'), logged_in(teacher):
        test_client.req(
            'get',
            base_url,
            200,
            result={
                'id': assignment['analytics_workspace_ids'][0],
                'assignment_id': assignment['id'],
                'student_submissions': {
                    str(get_id(student)): [{
                        'id': work_id,
                        'created_at': str,
                        'grade': None,
                        'assignee_id': None,
                    }],
                },
                'data_sources': lambda x: 'inline_feedback' in x,
            }
        )

    with describe('standard no comments'), logged_in(teacher):
        test(0)

    with describe('after adding reply it should return 1'), logged_in(teacher):
        r1 = add_reply('A reply', line=1)
        test(1)

    with describe('after two replies on 1 line should return 1'
                  ), logged_in(teacher):
        r2 = add_reply('A reply on the reply', line=1)
        test(1)

    with describe('a reply on another line should return more'
                  ), logged_in(teacher):
        r3 = add_reply('A new line reply', line=2)
        r4 = add_reply('WOW MUCH REPLIES', line=1000)
        test(3)

    with describe('Updating should not change a thing'), logged_in(teacher):
        test(3)
        r4 = r4.update('wow new text')
        test(3)

    with describe('after deleting replies it should be back at 0'
                  ), logged_in(teacher):
        # Should begin with 3
        test(3)

        # There is another comment on this line so it should stay the same
        r1.delete()
        test(3)
        r3.delete()
        test(2)
        r4.delete()
        test(1)
        r2.delete()
        test(0)

    with describe('students cannot access it'), logged_in(student):
        test_client.req('get', url, 403)


def test_getting_analytics_workspace(
    logged_in, test_client, session, admin_user, describe, tomorrow
):
    with describe('setup'), logged_in(admin_user):
        assignment = helpers.create_assignment(
            test_client, state='open', deadline=tomorrow
        )
        course = assignment['course']
        teacher = admin_user
        student = helpers.create_user_with_role(session, 'Student', course)

        work_id = helpers.get_id(
            helpers.create_submission(
                test_client, assignment, for_user=student
            )
        )

        base_url = (
            f'/api/v1/analytics/{assignment["analytics_workspace_ids"][0]}'
        )
        url = base_url + '/data_sources/rubric_data'

        def test(items):
            test_client.req(
                'get',
                url,
                200,
                result={
                    'name': 'rubric_data',
                    'data': {
                        str(work_id): [{
                            'item_id': get_id(item),
                            'multiplier': 1.0,
                        } for item in items]
                    },
                },
            )

    with describe('by default there should be not rubric data source'
                  ), logged_in(teacher):
        test_client.req(
            'get',
            base_url,
            200,
            result={
                'id': assignment['analytics_workspace_ids'][0],
                'assignment_id': assignment['id'],
                'student_submissions': {
                    str(get_id(student)): [{
                        'id': work_id,
                        'created_at': str,
                        'grade': None,
                        'assignee_id': None,
                    }],
                },
                'data_sources': lambda x: 'rubric_data' not in x,
            }
        )
        test_client.req('get', url, 404)

    with describe('After adding a rubric it should have the data source'
                  ), logged_in(teacher):
        rubric = test_client.req(
            'put',
            f'/api/v1/assignments/{get_id(assignment)}/rubrics/',
            200,
            data=RUBRIC
        )
        test_client.req(
            'get',
            base_url,
            200,
            result={
                'id': assignment['analytics_workspace_ids'][0],
                'assignment_id': assignment['id'],
                'student_submissions': {
                    str(get_id(student)): [{
                        'id': work_id,
                        'created_at': str,
                        'grade': None,
                        'assignee_id': None,
                    }],
                },
                'data_sources': lambda x: 'rubric_data' in x,
            }
        )
        test([])

    with describe('After selecting there are returned'), logged_in(teacher):
        to_select = [
            get_rubric_item(rubric, 'My header', '10points'),
            get_rubric_item(rubric, 'My header2', '2points'),
        ]

        for idx, item in enumerate(to_select):
            test_client.req(
                'patch',
                f'/api/v1/submissions/{work_id}/rubricitems/{item["id"]}',
                204,
            )

            test(to_select[:idx + 1])

    with describe('Changing item in header works'), logged_in(teacher):
        item = get_rubric_item(rubric, 'My header', '5points')
        to_select[0] = item
        test_client.req(
            'patch',
            f'/api/v1/submissions/{work_id}/rubricitems/{item["id"]}',
            204,
        )

        test(to_select)

    with describe('students cannot access it'), logged_in(student):
        test_client.req('get', url, 403)
