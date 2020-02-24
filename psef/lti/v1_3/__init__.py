import os
import sys
import json
import typing as t
import dataclasses

import werkzeug
import structlog
import sqlalchemy.sql
from typing_extensions import Final
from pylti1p3.deployment import Deployment
from pylti1p3.oidc_login import OIDCLogin
from pylti1p3.tool_config import ToolConfAbstract
from pylti1p3.registration import Registration
from pylti1p3.message_launch import MessageLaunch
from pylti1p3.deep_link_resource import DeepLinkResource

import flask
from cg_dt_utils import DatetimeWithTimezone
from cg_flask_helpers import callback_after_this_request

from . import claims
from ... import PsefFlask, tasks, models, helpers, current_app
from .flask import (
    FlaskRequest, FlaskRedirect, FlaskCookieService, FlaskSessionService
)
from .roles import SystemRole, ContextRole
from ...models import AssignmentVisibilityState, db
from ..abstract import AbstractLTIConnector
from ...exceptions import APICodes, APIException

logger = structlog.get_logger()

T = t.TypeVar('T')

if t.TYPE_CHECKING:
    from pylti1p3.message_launch import _JwtData, _LaunchData


class CGCustomClaims:
    @dataclasses.dataclass(frozen=True)
    class ClaimResult:
        username: str
        deadline: t.Optional[DatetimeWithTimezone]
        is_available: t.Optional[bool]
        assignment_id: t.Optional[int]

    @dataclasses.dataclass(frozen=True)
    class _Var:
        name: str
        opts: t.List[str]
        required: bool

        def get_key(self, idx: int) -> str:
            return f'{self.name}_{idx}'

    _WANTED_VARS: Final = [
        _Var('cg_username', ['$User.username'], True),
        _Var(
            'cg_deadline',
            [
                '$ResourceLinke.submission.endDateTime',
                '$Canvas.assignment.dueAt.iso8601'
            ],
            False,
        ),
        _Var(
            'cg_available_at',
            ['$ResourceLink.submission.startDateTime'],
            False,
        ),
        _Var('cg_is_published', ['$Canvas.assignment.published'], False)
    ]

    _VAR_LOOKUP: Final = {var.name: var for var in _WANTED_VARS}

    _WANTED_PERMA: t.List[
        t.Tuple[str, t.Callable[['CGCustomCalims'], str]]] = [
            ('cg_assignment_id', lambda self: str(self._assig.id))
        ]

    def __init__(self, assignment: models.Assignment) -> None:
        self._assig = assignment

    def get_claims_config(self) -> t.Mapping[str, str]:
        res: t.Dict[str, str] = {}
        for var in self._WANTED_VARS:
            for idx, value in enumerate(var.opts):
                res[var.get_key(idx)] = value

        for key, producer in self._WANTED_PERMA:
            res[key] = producer(self)

        return res

    @classmethod
    def get_claim_keys(cls) -> t.Iterable[str]:
        for var in cls._WANTED_VARS:
            for idx, _ in enumerate(var.opts):
                yield var.get_key(idx)

        for key, producer in cls._WANTED_PERMA:
            yield key

    @classmethod
    def _get_claim(
        cls,
        var_name: str,
        data: t.Mapping[str, str],
        converter: t.Callable[[str], T],
    ) -> t.Optional[T]:
        var = cls._VAR_LOOKUP[var_name]

        for idx, default_val in enumerate(var.opts):
            found_val = data.get(var.get_key(idx), default_val)
            if found_val != default_val:
                return converter(found_val)

        assert not var.required, 'Required variable was not found'
        return None

    @classmethod
    def get_custom_claim_data(
        cls, launch_data: '_LaunchData'
    ) -> 'CGCustomClaims.ClaimResult':
        data = launch_data[claims.CUSTOM]
        username = cls._get_claim('cg_username', data, lambda x: x)
        # Username is a required var
        assert username is not None

        deadline = cls._get_claim(
            'cg_deadline', data, DatetimeWithTimezone.parse_isoformat
        )

        available_at = cls._get_claim(
            'cg_available_at', data, DatetimeWithTimezone.parse_isoformat
        )
        if available_at is None:
            is_available = cls._get_claim(
                'cg_is_published', data, lambda x: x == 'true'
            )
        else:
            is_available = DatetimeWithTimezone.utcnow() >= available_at

        try:
            assignment_id: t.Optional[int] = int(data['cg_assignment_id'])
        except (KeyError, ValueError):
            assignment_id = None

        return CGCustomClaims.ClaimResult(
            username=username,
            deadline=deadline,
            is_available=is_available,
            assignment_id=assignment_id,
        )


class CGDeepLinkResource(DeepLinkResource):
    def __init__(self, *, assignment: 'models.Assignment') -> None:
        super().__init__()

        self.set_type('ltiResourceLink')
        self.set_title(assignment.name)
        self.set_custom_params(
            CGCustomClaims(assignment=assignment).get_claims_config()
        )
        self._assig = assignment

    def to_dict(self) -> t.Dict[str, object]:
        res = super().to_dict()
        assert self._assig.deadline is not None
        res['submission'] = {
            'endDateTime': self._assig.deadline.isoformat(),
        }
        return res


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

    def get_assignment_or_none(self, course: models.Course
                               ) -> t.Optional[models.Assignment]:
        custom_claim = self.get_custom_claims()

        res = models.Assignment.query.filter(
            models.Assignment.id == custom_claim.assignment_id,
            models.Assignment.course == course,
        )

        return res.one_or_none()

    def create_deep_link_assignment(
        self, course: models.Course
    ) -> models.Assignment:
        assignment = self.get_assignment_or_none(course)
        if assignment:
            return assignment

        assignment = models.Assignment(
            course=course,
            visibility_state=AssignmentVisibilityState.deep_linked,
            is_lti=True,
        )

        return assignment

    def get_assignment(
        self, user: models.User, course: models.Course
    ) -> models.Assignment:
        launch_data = self.get_launch_data()
        resource_claim = launch_data[claims.RESOURCE]
        custom_claim = self.get_custom_claims()

        resource_id = resource_claim['id']

        assignment = self.get_assignment_or_none(course)
        logger.bind(assignment=assignment)
        logger.info('Searching for existing assignment')

        if assignment is not None and assignment.is_deep_linked:
            assignment.visibility_state = AssignmentVisibilityState.visible
            assignment.lti_assignment_id = resource_id
        elif assignment is None or assignment.lti_assignment_id != resource_id:
            raise APIException(
                (
                    'The assignment was not found on CodeGrade, please'
                    ' initiate a DeepLink when creating an LTI Assignment'
                ), f'The assignment "{resource_id}" was not found',
                APICodes.OBJECT_NOT_FOUND, 404
            )

        if custom_claim.deadline is not None:
            assignment.deadline = custom_claim.deadline

        # This claim is not required by the LTI spec, so we simply don't
        # override the assignment name if it is not given or if it is empty.
        if resource_claim.get('title'):
            assignment.name = resource_claim['title']

        if not assignment.is_done:
            if custom_claim.is_available is None or custom_claim.is_available:
                assignment.state = models._AssignmentStateEnum.open
            else:
                assignment.state = models._AssignmentStateEnum.hidden

        return assignment

    def set_user_course_role(self, user: models.User,
                             course: models.Course) -> t.Optional[str]:
        assert course.course_lti_provider
        return course.course_lti_provider.maybe_add_user_to_course(
            user,
            self.get_launch_data()[claims.ROLES],
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
        """Check that all data required by CodeGrade is present.
        """
        launch_data = self.get_launch_data()

        def get_exc(
            msg: str,
            claim: t.Union[None, t.Mapping, t.Sequence[str]],
            missing: t.List[str],
        ) -> APIException:
            return APIException(
                msg,
                f'The claim "{claim}" was missing the following keys: {missing}',
                APICodes.MISSING_REQUIRED_PARAM, 400
            )

        def check_and_raise(
            msg: str,
            mapping: t.Optional[t.Mapping[str, object]],
            *keys: str,
        ) -> None:
            if mapping:
                missing = [key for key in keys if not mapping.get(key)]
            else:
                missing = ['__ALL__']

            if missing:
                raise get_exc(msg, mapping, missing)

        check_and_raise(
            (
                'We are missing required data about the user doing this LTI'
                ' launch, please check the privacy levels of the tool:'
                ' CodeGrade requires the email and the name of the user.'
            ), launch_data, 'email', 'name'
        )

        context = launch_data.get(claims.CONTEXT)
        check_and_raise(
            'The LTI launch did not contain a context', context, 'id', 'title'
        )

        custom = launch_data[claims.CUSTOM]
        check_and_raise(
            (
                'The LTI launch is missing required custom claims, the setup'
                ' was probably done incorrectly'
            ), custom, *CGCustomClaims.get_claim_keys()
        )

        if not self.has_nrps():
            raise get_exc(
                (
                    'It looks like the NamesRoles Provisioning service is not'
                    ' enabled for this LTI deployment, please check your'
                    ' configuration'
                ),
                launch_data.get(claims.NAMESROLES),
                [],
            )

        ags = launch_data.get(claims.GRADES, {})
        check_and_raise(
            (
                'It looks like the Assignments and Grades service is not'
                ' enabled for this LTI deployment, please check your'
                ' configuration'
            ), ags, 'scope'
        )

        scopes = ags.get('scope', [])
        needed_scopes = [
            'https://purl.imsglobal.org/spec/lti-ags/scope/score',
            'https://purl.imsglobal.org/spec/lti-ags/scope/lineitem',
        ]
        check_and_raise(
            (
                'We do not have the required permissions for passing back'
                ' grades and updating deadlines in the LMS, please check your'
                ' configuration'
            ),
            {s: True
             for s in scopes},
            *needed_scopes,
        )

        # We don't need to check the roles claim, as that is required by spec
        # to always exist. The same for the resource claim, it is also
        # required.

        return self

    def validate(self) -> 'FlaskMessageLaunch':
        super().validate()

        try:
            return self.validate_has_needed_data()
        except:
            self._validated = False
            raise

    def get_custom_claims(self) -> CGCustomClaims.ClaimResult:
        return CGCustomClaims.get_custom_claim_data(self.get_launch_data())

    def ensure_lti_user(
        self
    ) -> t.Tuple[models.User, t.Optional[str], t.Optional[str]]:
        launch_data = self.get_launch_data()
        custom_claims = self.get_custom_claims()

        user, token = models.UserLTIProvider.get_or_create_user(
            lti_user_id=launch_data['sub'],
            lti_provider=self.get_lti_provider(),
            wanted_username=custom_claims.username,
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
        launch_data = self.get_launch_data()
        deployment_id = self._get_deployment_id()
        context_claim = launch_data[claims.CONTEXT]
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
        course_lti_provider.names_roles_claim = launch_data[claims.NAMESROLES]

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
