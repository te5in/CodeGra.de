import os
import sys
import json
import typing as t

import flask
import werkzeug
import structlog
from pylti1p3.deployment import Deployment
from pylti1p3.oidc_login import OIDCLogin
from pylti1p3.tool_config import ToolConfAbstract
from pylti1p3.registration import Registration
from pylti1p3.message_launch import MessageLaunch

from cg_dt_utils import DatetimeWithTimezone
from cg_flask_helpers import callback_after_this_request

from . import claims
from ... import PsefFlask, tasks, models, helpers, current_app
from .flask import (
    FlaskRequest, FlaskRedirect, FlaskCookieService, FlaskSessionService
)
from .roles import SystemRole, ContextRole
from ...models import db
from ..abstract import AbstractLTIConnector

logger = structlog.get_logger()

if t.TYPE_CHECKING:
    from pylti1p3.message_launch import _JwtData


def init_app(app: PsefFlask) -> None:
    app.config['LTI1.3_CONFIG_JSON'] = {}
    app.config['LTI1.3_CONFIG_DIRNAME'] = ''

    path = app.config['_LTI1.3_CONFIG_JSON_PATH']
    if path is not None:
        app.config['LTI1.3_CONFIG_DIRNAME'] = os.path.dirname(path)
        with open(path, 'r') as f:
            conf = json.load(f)

            # Make sure the config is a t.Mapping[str, t.Mapping[str, str]]
            assert all(
                (
                    isinstance(v, dict) and
                    all(isinstance(vv, str) for vv in v.values())
                ) for v in conf.values()
            )

            app.config['LTI1.3_CONFIG_JSON'] = conf


class LTIConfig(ToolConfAbstract):
    def find_registration_by_issuer_and_client(
        self, iss: str, client_id: t.Optional[str]
    ) -> t.Optional[Registration]:
        if client_id is None:
            return self.find_registration_by_issuer(iss)

        return helpers.filter_single_or_404(
            models.LTI1p3Provider,
            models.LTI1p3Provider.iss == iss,
            models.LTI1p3Provider.client_id == client_id,
        ).get_registration()

    def find_registration_by_issuer(self, iss: str) -> Registration:
        return helpers.filter_single_or_404(
            models.LTI1p3Provider,
            models.LTI1p3Provider.iss == iss,
        ).get_registration()

    def find_deployment(
        self,
        iss: str,
        deployment_id: str,
    ) -> t.Optional[Deployment]:
        return None


class FlaskMessageLaunch(
    AbstractLTIConnector,
    MessageLaunch[FlaskRequest, LTIConfig, FlaskSessionService,
                  FlaskCookieService]
):
    _provider: t.Optional[models.LTI1p3Provider] = None

    def get_lms_name(self) -> str:
        return self.get_lti_provider().lms_name

    def set_user_role(self, user: models.User) -> None:
        """Set the role of the given user if the user has no role.

        If the role could not be matched the ``DEFAULT_ROLE`` configured in the
        config of the app is used.

        :param models.User user: The user to set the role for.
        """
        if user.role is not None:
            return

        roles_claim = self.get_launch_data()[claims.ROLES]
        global_roles = SystemRole.parse_roles(roles_claim)
        logger.info(
            'Checking global roles',
            given_global_roles=global_roles,
            roles_claim=roles_claim,
        )

        role_name = (
            global_roles[0].codegrade_role_name
            if global_roles else current_app.config['DEFAULT_ROLE']
        )
        user.role = models.Role.query.filter(
            models.Role.name == role_name,
        ).one()

    def get_assignment(
        self, user: models.User, course: models.Course
    ) -> models.Assignment:
        launch_data = self.get_launch_data()
        resource_claim = launch_data[claims.RESOURCE]
        resource_id = resource_claim['id']
        custom_claim = launch_data[claims.CUSTOM]

        assignment = models.Assignment.query.filter(
            models.Assignment.lti_assignment_id == resource_id,
            models.Assignment.course == course,
        ).one_or_none()
        logger.info('Searching for existing assignment', assignment=assignment)
        if assignment is None:
            # TODO: Create assignment from deep link data
            logger.info(
                'No assignment found in course', lti_assignment_id=resource_id
            )
            assignment = models.Assignment(
                lti_assignment_id=resource_id, course=course
            )
            db.session.add(assignment)
            db.session.flush()
        logger.bind(assignment=assignment)

        deadline = custom_claim['cg_deadline']
        if deadline != '$ResourceLink.submission.endDateTime':
            assignment.deadline = DatetimeWithTimezone.parse_isoformat(
                deadline,
            )

        available_at = custom_claim['cg_available_at']
        logger.info(
            'Checking if assignment is available',
            available_at=available_at,
        )
        if not assignment.is_done:
            now = DatetimeWithTimezone.utcnow()
            if available_at == '$ResourceLink.available.startDateTime':
                is_open = True
            else:
                is_open = now >= DatetimeWithTimezone.parse_isoformat(
                    available_at
                )

            logger.info(
                'Setting assignment state',
                assignment_is_open=is_open,
                used_now=now
            )
            if is_open:
                assignment.state = models._AssignmentStateEnum.open
            else:
                assignment.state = models._AssignmentStateEnum.hidden

        return assignment

    @staticmethod
    def add_user_to_course(
        user: models.User, course: models.Course, roles_claim: t.List[str]
    ) -> t.Optional[str]:
        roles = ContextRole[str].parse_roles(roles_claim)
        logger.info(
            'Finding role for user',
            roles_claim=roles_claim,
            parsed_context_roles=roles,
        )
        if roles:
            user.enroll_in_course(
                course_role=db.session.query(models.CourseRole).filter(
                    models.CourseRole.name == roles[0].codegrade_role_name,
                    models.CourseRole.course == course,
                    ~models.CourseRole.hidden,
                ).one()
            )
            return None

        unmapped_roles = ContextRole[None].get_umapped_roles(roles_claim)
        if unmapped_roles:
            logger.info(
                'No mapped LTI roles found, searching for unmapped roles',
                unmapped_roles=unmapped_roles,
            )

            base = 'Unmapped LTI Role ({})'
            for unmapped_role in unmapped_roles:
                role = db.session.query(models.CourseRole).filter(
                    models.CourseRole.name == base.format(unmapped_role.name),
                    models.CourseRole.course == course,
                    ~models.CourseRole.hidden,
                ).one_or_none()
                if role:
                    user.enroll_in_course(course_role=role)
                    return None

            new_role_name = base.format(unmapped_roles[0].name)
        else:
            base = 'New LTI Role'
            for idx in range(sys.maxsize):
                if not db.session.query(
                    db.session.query(models.CourseRole).filter(
                        models.CourseRole.name == base.format(idx=idx),
                        models.CourseRole.course == course,
                    ).exists()
                ).scalar():
                    break
                base = 'New LTI Role ({idx})'
            new_role_name = base.format(idx=idx)

        logger.info('Creating new role', new_role_name=new_role_name)
        role = models.CourseRole(
            course=course,
            name=new_role_name,
            hidden=False,
        )
        db.session.add(role)
        db.session.flush()

        user.enroll_in_course(course_role=role)
        return role.name

    def set_user_course_role(self, user: models.User,
                             course: models.Course) -> t.Optional[str]:
        if user.is_enrolled(course):
            return None

        callback_after_this_request(
            lambda: tasks.update_members_in_lti_course(course.id)
        )
        return self.add_user_to_course(
            user,
            course,
            roles_claim=self.get_launch_data()[claims.ROLES],
        )

    def _get_request_param(self, key: str) -> object:
        return self._request.get_param(key)

    @classmethod
    def from_request(cls, request: flask.Request) -> 'FlaskMessageLaunch':
        return cls(
            FlaskRequest(request, force_post=True),
            LTIConfig(),
            FlaskSessionService(request),
            FlaskCookieService(request),
        )

    def get_lti_provider(self) -> models.LTI1p3Provider:
        if self._provider is None:
            assert self._registration is not None

            client_id = self._registration.get_client_id()
            self._provider = helpers.filter_single_or_404(
                models.LTI1p3Provider,
                models.LTI1p3Provider.iss == self._get_iss(),
                models.LTI1p3Provider.client_id == client_id,
            )
        return self._provider

    # We never want to save the launch data in the session, as we have no
    # use-case for it, and it slows down every request
    def save_launch_data(self) -> 'FlaskMessageLaunch':
        return self

    def validate_deployment(self) -> 'FlaskMessageLaunch':
        return self

    def validate_has_needed_data(self) -> 'FlaskMessageLaunch':
        # TODO: Check that all needed data is present
        return self

    def validate(self) -> 'FlaskMessageLaunch':
        super().validate()

        try:
            return self.validate_has_needed_data()
        except:
            self._validated = False
            raise

    def ensure_lti_user(
        self
    ) -> t.Tuple[models.User, t.Optional[str], t.Optional[str]]:
        launch_data = self.get_launch_data()
        custom_claims = launch_data[claims.CUSTOM]

        user, token = models.UserLTIProvider.get_or_create_user(
            lti_user_id=launch_data['sub'],
            lti_provider=self.get_lti_provider(),
            wanted_username=custom_claims['cg_username'],
            full_name=launch_data['name'],
            email=launch_data['email'],
        )

        updated_email = None
        if user.reset_email_on_lti:
            user.email = launch_data['email']
            updated_email = user.email
            user.reset_email_on_lti = False

        return user, token, updated_email

    def get_course(self) -> models.Course:
        deployment_id = self._get_deployment_id()
        context_claim = self.get_launch_data()[claims.CONTEXT]
        course_lti_provider = db.session.query(
            models.CourseLTIProvider
        ).filter(
            models.CourseLTIProvider.deployment_id == deployment_id,
            models.CourseLTIProvider.lti_course_id == context_claim['id'],
            models.CourseLTIProvider.lti_provider == self.get_lti_provider(),
        ).one_or_none()

        if course_lti_provider is None:
            course = models.Course.create_and_add(name=context_claim['title'])
            course_lti_provider = models.CourseLTIProvider.create_and_add(
                course=course,
                lti_provider=self.get_lti_provider(),
                lti_context_id=context_claim['id'],
                deployment_id=deployment_id,
            )
            models.db.session.flush()
        else:
            course = course_lti_provider.course
            course.name = context_claim['title']

        return course

    @classmethod
    def from_message_data(
        cls,
        request: flask.Request,
        launch_data: t.Mapping[str, object],
    ) -> 'FlaskMessageLaunch':
        obj = cls(
            FlaskRequest(request, force_post=False),
            LTIConfig(),
            session_service=FlaskSessionService(request),
            cookie_service=FlaskCookieService(request),
        )

        return obj.set_auto_validation(enable=False) \
            .set_jwt(t.cast('_JwtData', {'body': launch_data})) \
            .set_restored() \
            .validate_registration()


class FlaskOIDCLogin(
    OIDCLogin[FlaskRequest, LTIConfig, FlaskSessionService, FlaskCookieService,
              werkzeug.wrappers.Response]
):
    def get_redirect(self, url: str) -> FlaskRedirect:
        return FlaskRedirect(url, self._cookie_service)

    @classmethod
    def from_request(cls, request: flask.Request) -> 'FlaskOIDCLogin':
        return FlaskOIDCLogin(
            FlaskRequest(request, force_post=False),
            LTIConfig(),
            FlaskSessionService(request),
            FlaskCookieService(request),
        )
