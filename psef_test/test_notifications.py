import re
import datetime

import pytest
from freezegun import freeze_time

import psef
import helpers
import psef.models as m
from helpers import get_id
from test_feedback import mail_functions, make_add_reply


def test_direct_emails_in_thread(
    logged_in, test_client, session, admin_user, mail_functions, describe,
    tomorrow, make_add_reply
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
        add_reply('base comment', include_response=True)

    with describe('Initial reply should not be send in a thread'
                  ), logged_in(student):
        add_reply('first reply')
        first_msg, = mail_functions.assert_mailed(teacher)
        assert 'first reply' in first_msg.msg
        assert student.name in first_msg.msg
        assert first_msg.in_reply_to is None

    with describe('Own replies should not be mailed'), logged_in(teacher):
        add_reply('own reply')
        mail_functions.assert_mailed(teacher, amount=0)

    with describe('Second reply should be send as reply to first message'
                  ), logged_in(student):
        add_reply('second reply')
        second_msg, = mail_functions.assert_mailed(teacher)
        assert 'first reply' not in second_msg.msg
        assert 'second reply' in second_msg.msg
        assert student.name in second_msg.msg
        assert second_msg.in_reply_to == first_msg.message_id
        assert second_msg.references == [first_msg.message_id]

    with describe('Third reply should be send as reply to first message'
                  ), logged_in(student):
        add_reply('third reply')
        third_msg, = mail_functions.assert_mailed(teacher)
        assert third_msg.in_reply_to == first_msg.message_id
        assert third_msg.references == [first_msg.message_id]


def test_send_mails(
    logged_in, test_client, session, admin_user, mail_functions, describe,
    tomorrow, make_add_reply
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

        url = '/api/v1/settings/notification_settings/'
        add_reply = make_add_reply(work_id)
        add_reply('base comment', include_response=True)

    with describe('default should send mail'):
        with logged_in(teacher):
            test_client.req(
                'get',
                url,
                200,
                result={
                    'options': [
                        {
                            'reason': 'assignee',
                            'explanation': str,
                            'value': 'direct',
                        },
                        {
                            'reason': 'author',
                            'explanation': str,
                            'value': 'off',
                        },
                        {
                            'reason': 'replied',
                            'explanation': str,
                            'value': 'direct',
                        },
                    ],
                    'possible_values': ['direct', 'daily', 'weekly', 'off'],
                }
            )

        with logged_in(student):
            add_reply('first reply')
            msg, = mail_functions.assert_mailed(teacher)

    with describe('Preferences can be changed as logged in user'):
        with logged_in(teacher):
            test_client.req(
                'patch',
                url,
                204,
                data={'reason': 'replied', 'value': 'daily'}
            )

        with logged_in(student):
            add_reply('first reply')
            mail_functions.assert_mailed(teacher, amount=0)

            psef.tasks._send_daily_notifications()
            mail_functions.assert_mailed(teacher, amount=1)
            assert mail_functions.digest.called
            assert not mail_functions.direct.called

    with describe('Mails should not be send multiple times'):
        psef.tasks._send_daily_notifications()
        mail_functions.assert_mailed(teacher, amount=0)

    with describe('Fastest setting should be used'):
        m.Work.query.filter_by(id=work_id).update({
            'assigned_to': teacher.id,
        })
        session.commit()
        with logged_in(teacher):
            for reason, value in [('replied', 'daily'), ('assignee',
                                                         'weekly')]:
                test_client.req(
                    'patch', url, 204, data={'reason': reason, 'value': value}
                )

        with logged_in(student):
            add_reply('first reply')
            psef.tasks._send_weekly_notifications()
            # Should not be send as a more specific is available
            mail_functions.assert_mailed(teacher, amount=0)

            # Should be send as this is the most specific enabled setting
            psef.tasks._send_daily_notifications()
            mail_functions.assert_mailed(teacher, amount=1)

    with describe('should not send when comment is deleted'):
        with logged_in(student):
            reply = add_reply('reply that will be deleted')
        with logged_in(teacher):
            reply.delete()

        psef.tasks._send_daily_notifications()
        mail_functions.assert_mailed(teacher, amount=0)

    with describe('Preferences can be changed using the mailed token'):
        token = re.search(
            r'unsubscribe/email_notifications/\?token=([^"]+)"', msg.msg
        ).group(1)
        assert '"' not in token
        test_client.req(
            'patch',
            url + '?token=' + token,
            204,
            data={'reason': 'replied', 'value': 'direct'}
        )

        with logged_in(student):
            add_reply('third reply')
            mail_functions.assert_mailed(teacher, amount=1)

    with describe('Tokens can be reused for a few days'):
        test_client.req(
            'patch',
            url + '?token=' + token,
            204,
            data={'reason': 'assignee', 'value': 'direct'}
        )

        with freeze_time(
            datetime.datetime.utcnow() + datetime.timedelta(days=10)
        ):
            test_client.req(
                'patch',
                url + '?token=' + token,
                403,
                data={'reason': 'assignee', 'value': 'direct'}
            )

    with describe('Tokens should not be random garbage'):
        test_client.req(
            'patch',
            url + '?token=' + 'random_garbage',
            403,
            data={'reason': 'assignee', 'value': 'direct'}
        )


def test_updating_notifications(
    logged_in, test_client, session, admin_user, mail_functions, describe,
    tomorrow, make_add_reply
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
        add_reply('base comment', include_response=True)

        with logged_in(student):
            r1 = add_reply('first reply')
            r2 = add_reply('second reply')
            r3 = add_reply('third reply')
            r4 = add_reply('fourth reply')

    with describe('Can get all notifications'), logged_in(teacher):
        notis = test_client.req(
            'get',
            '/api/v1/notifications/?has_unread',
            200,
            result={'has_unread': True}
        )
        notis = test_client.req(
            'get', '/api/v1/notifications/', 200, {
                'notifications': [
                    {
                        'read': False,
                        '__allow_extra__': True,
                        'comment_reply': r4,
                    },
                    {
                        'read': False,
                        '__allow_extra__': True,
                        'comment_reply': r3,
                    },
                    {
                        'read': False,
                        '__allow_extra__': True,
                        'comment_reply': r2,
                    },
                    {
                        'read': False,
                        '__allow_extra__': True,
                        'comment_reply': r1,
                    },
                ]
            }
        )['notifications']

    with describe('Can update single notification'), logged_in(teacher):
        noti = notis.pop(0)
        noti = test_client.req(
            'patch',
            f'/api/v1/notifications/{get_id(noti)}',
            200,
            data={
                'read': True,
            }
        )
        notis.append(noti)
        print(notis)
        notis = test_client.req(
            'get', '/api/v1/notifications/', 200, {'notifications': notis}
        )['notifications']

    with describe('Can update bulk notifications'), logged_in(teacher):
        # Update the first two notifications (those sould now become the last
        # two)
        notis += test_client.req(
            'patch',
            f'/api/v1/notifications/',
            200,
            data={
                'notifications': [{
                    'id': n['id'],
                    'read': True,
                } for n in [notis.pop(0), notis.pop(0)]],
            }
        )['notifications']

        notis = test_client.req(
            'get', '/api/v1/notifications/', 200, {'notifications': notis}
        )['notifications']

    with describe('cannot update notifications for deleted replies'
                  ), logged_in(teacher):
        # Make sure the notification we are going to update is that of the
        # deleted reply
        assert notis[0]['comment_reply']['id'] == r1['id']
        r1.delete()

        test_client.req(
            'patch',
            f'/api/v1/notifications/',
            404,
            data={
                'notifications': [{'id': notis[0]['id'], 'read': True}],
            }
        )
        test_client.req(
            'patch',
            f'/api/v1/notifications/{notis[0]["id"]}',
            404,
            data={'read': True}
        )

    with describe('Cannot update notifications of others'), logged_in(student):
        # Make sure this not the notification of the deleted reply
        assert notis[-1]['comment_reply']['id'] != r1['id']
        test_client.req(
            'patch',
            f'/api/v1/notifications/',
            403,
            data={
                'notifications': [{'id': notis[-1]['id'], 'read': True}],
            }
        )
        test_client.req(
            'patch',
            f'/api/v1/notifications/{notis[-1]["id"]}',
            403,
            data={'read': True}
        )
