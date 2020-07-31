import uuid
from datetime import timedelta

import structlog

from cg_json import JSONResponse, ExtendedJSONResponse

from . import api
from .. import auth, models, helpers
from .login import LoginResponse
from ..errors import APICodes, APIException
from ..models import db
from ..helpers import jsonify_options, get_request_start_time

logger = structlog.get_logger()


@api.route('/login_links/<uuid:login_link_id>')
def get_login_link(login_link_id: uuid.UUID
                   ) -> JSONResponse[models.AssignmentLoginLink]:
    login_link = helpers.get_or_404(
        models.AssignmentLoginLink,
        login_link_id,
        also_error=lambda l:
        (not l.assignment.is_visible or not l.assignment.send_login_links)
    )

    auth.set_current_user(login_link.user)
    return JSONResponse.make(login_link)


@api.route('/login_links/<uuid:login_link_id>/login', methods=['POST'])
def login_with_link(login_link_id: uuid.UUID
                    ) -> ExtendedJSONResponse[LoginResponse]:
    login_link = helpers.get_or_404(
        models.AssignmentLoginLink,
        login_link_id,
        also_error=lambda l:
        (not l.assignment.is_visible or not l.assignment.send_login_links)
    )
    assignment = login_link.assignment
    if assignment.deadline is None or assignment.deadline_expired:
        raise APIException
    elif assignment.state.is_hidden:
        assignment_id = assignment.id
        db.session.expire(assignment)

        assignment = models.Assignment.query.filter(
            models.Assignment.id == assignment_id
        ).with_for_update().one()
        logger.info(
            'Assignment is still hidden, checking if we have to open it',
            assignment_id=assignment_id,
            state=assignment.state,
            available_at=assignment.available_at,
        )

        if assignment.state.is_hidden:
            now = helpers.get_request_start_time()
            if (
                assignment.available_at is not None and
                now >= assignment.available_at
            ):
                assignment.state = models.AssignmentStateEnum.open
                db.session.commit()
            else:
                raise APIException

    logger.info(
        'Logging in user with login link', user_to_login=login_link.user
    )

    auth.set_current_user(login_link.user)

    auth.AssignmentPermissions(login_link.assignment).ensure_may_see()
    jsonify_options.get_options().add_permissions_to_user = login_link.user

    return ExtendedJSONResponse.make(
        {
            'user': login_link.user,
            'access_token':
                login_link.user.make_access_token(
                    expires_at=(
                        login_link.assignment.deadline + timedelta(minutes=30)
                    ),
                    for_course=login_link.assignment.course,
                ),
        },
        use_extended=models.User,
    )
