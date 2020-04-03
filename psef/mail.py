"""
This module is used for all mailing related tasks.

SPDX-License-Identifier: AGPL-3.0-only
"""
import html
import typing as t

import jinja2
import html2text
import structlog
from flask import current_app
from flask_mail import Mail, Message

import psef
import psef.models as models
from psef.errors import APICodes, APIException

from . import auth
from .helpers import readable_join

mail = Mail()  # pylint: disable=invalid-name
logger = structlog.get_logger()


def _send_mail(
    html_body: str,
    subject: str,
    recipients: t.Optional[t.Sequence[t.Union[str, t.Tuple[str, str]]]],
    mailer: t.Optional[Mail] = None,
    message_id: str = None,
    in_reply_to: str = None,
    references: t.List[str] = None,
) -> None:
    logger.info(
        'Sending email',
        subject=subject,
        html_body=html_body,
        recipients=recipients,
    )
    if recipients:
        if mailer is None:
            mailer = mail

        text_maker = html2text.HTML2Text(bodywidth=78)
        text_maker.inline_links = False
        text_maker.wrap_links = False
        extra_headers = {}

        if message_id is not None:
            extra_headers['Message-ID'] = message_id
        if in_reply_to is not None:
            extra_headers['In-Reply-To'] = in_reply_to
        if references:
            extra_headers['References'] = ' '.join(references)

        message = Message(
            subject=subject,
            body=text_maker.handle(html_body),
            html=html_body,
            recipients=recipients,
            extra_headers=extra_headers,
        )

        mailer.send(message)


def send_whopie_done_email(assig: models.Assignment) -> None:
    """Send whoepie done email for the given assignment.

    :param assig: The assignment to send the mail for.
    :returns: Nothing
    """
    html_body = current_app.config['DONE_TEMPLATE'].replace(
        '\n\n',
        '<br><br>',
    ).format(
        site_url=current_app.config['EXTERNAL_URL'],
        assig_id=assig.id,
        assig_name=html.escape(assig.name),
        course_id=assig.course_id,
    )

    recipients = psef.parsers.parse_email_list(assig.done_email)
    _send_mail(
        html_body,
        (
            f'Grading has finished for {assig.name} on '
            f'{current_app.config["EXTERNAL_URL"]}'
        ),
        recipients,
    )


def send_grader_status_changed_mail(
    assig: models.Assignment, user: models.User
) -> None:
    """Send grader status changed mail.

    :param assig: The assignment of which the status has changed.
    :param user: The user whose status has changed.
    :returns: Nothing
    """
    html_body = current_app.config['GRADER_STATUS_TEMPLATE'].replace(
        '\n\n', '<br><br>'
    ).format(
        site_url=current_app.config['EXTERNAL_URL'],
        assig_id=assig.id,
        user_name=html.escape(user.name),
        user_email=html.escape(user.email),
        assig_name=html.escape(assig.name),
        course_id=assig.course_id,
    )

    _send_mail(
        html_body,
        (
            f'Grade status toggled for {assig.name} on '
            f'{current_app.config["EXTERNAL_URL"]}'
        ),
        [user.email],
    )


def send_grade_reminder_email(
    assig: models.Assignment,
    user: models.User,
    mailer: Mail,
) -> None:
    """Remind a user to grade a given assignment.

    :param assig: The assignment that has to be graded.
    :param user: The user that should resume/start grading.
    :mailer: The mailer used to mail, this is important for performance.
    :returns: Nothing
    """
    html_body = current_app.config['REMINDER_TEMPLATE'].replace(
        '\n\n', '<br><br>'
    ).format(
        site_url=current_app.config['EXTERNAL_URL'],
        assig_id=assig.id,
        user_name=html.escape(user.name),
        user_email=html.escape(user.email),
        assig_name=html.escape(assig.name),
        course_id=assig.course_id,
    )
    _send_mail(
        html_body,
        (
            f'Grade reminder for {assig.name} on '
            f'{current_app.config["EXTERNAL_URL"]}'
        ),
        [user.email],
        mailer,
    )


def send_reset_password_email(user: models.User) -> None:
    """Send the reset password email to a user.

    :param user: The user that has requested a reset password email.
    :returns: Nothing
    """
    token = user.get_reset_token()
    html_body = current_app.config['EMAIL_TEMPLATE'].replace(
        '\n\n', '<br><br>'
    ).format(
        site_url=current_app.config["EXTERNAL_URL"],
        url=(
            f'{current_app.config["EXTERNAL_URL"]}/reset_'
            f'password/?user={user.id}&token={token}'
        ),
        user_id=user.id,
        token=token,
        user_name=html.escape(user.name),
        user_email=html.escape(user.email),
    )
    try:
        _send_mail(
            html_body, f'Reset password on {psef.app.config["EXTERNAL_URL"]}',
            [user.email]
        )
    except Exception:
        logger.bind(exc_info=True)
        raise APIException(
            'Something went wrong sending the email, '
            'please contact your site admin',
            f'Sending email to {user.id} went wrong.',
            APICodes.UNKOWN_ERROR,
            500,
        )


def send_digest_notification_email(
    notifications: t.List[models.Notification],
    send_type: models.EmailNotificationTypes,
) -> None:
    if not notifications:
        return

    receiver = notifications[0].receiver
    assert all(n.receiver == receiver for n in notifications)

    settings_token = models.NotificationsSetting.get_settings_change_token(
        receiver
    )

    reasons = readable_join(
        sorted(
            set(
                expl for n in notifications
                for _, expl in n.reasons_with_explanation
            )
        )
    )
    with auth.as_current_user(receiver):
        subject = current_app.jinja_mail_env.from_string(
            current_app.config['DIGEST_NOTIFICATION_SUBJECT']
        ).render(
            site_url=current_app.config["EXTERNAL_URL"],
            notifications=notifications,
            send_type=send_type,
        )

        html_body = current_app.jinja_mail_env.get_template(
            'digest.j2'
        ).render(
            site_url=current_app.config["EXTERNAL_URL"],
            notifications=notifications,
            subject=subject,
            send_type=send_type,
            receiver=receiver,
            reasons=reasons,
            settings_token=settings_token,
        )

    _send_mail(
        html_body,
        subject,
        [receiver.email],
    )


def send_direct_notification_email(notification: models.Notification) -> None:
    comment = notification.comment_reply

    references = [r.message_id for r in comment.references]
    first_reply = comment.comment_base.first_reply
    in_reply_to_message_id = None

    if first_reply is not None and first_reply.id != comment.id:
        in_reply_to_message_id = first_reply.message_id
        references.append(in_reply_to_message_id)
    references.reverse()

    settings_token = models.NotificationsSetting.get_settings_change_token(
        notification.receiver
    )

    with auth.as_current_user(notification.receiver):
        subject = current_app.jinja_mail_env.from_string(
            current_app.config['DIRECT_NOTIFICATION_SUBJECT']
        ).render(
            site_url=current_app.config["EXTERNAL_URL"],
            notification=notification,
            settings_token=settings_token,
        )

        html_body = current_app.jinja_mail_env.get_template(
            'notification.j2'
        ).render(
            site_url=current_app.config["EXTERNAL_URL"],
            notification=notification,
            subject=subject,
            settings_token=settings_token,
            reasons=readable_join(
                [expl for _, expl in notification.reasons_with_explanation]
            ),
        )

    _send_mail(
        html_body,
        subject, [notification.receiver.email],
        message_id=comment.message_id,
        in_reply_to=in_reply_to_message_id,
        references=references,
    )


def init_app(app: t.Any) -> None:
    mail.init_app(app)
