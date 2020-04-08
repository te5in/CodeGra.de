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
            test_client.req(
                'delete', (
                    f'/api/v1/comments/{reply["comment_base_id"]}/'
                    f'replies/{reply["id"]}'
                ), 204
            )

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
