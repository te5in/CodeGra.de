import copy
import typing as t
import dataclasses
import urllib.parse

import requests
import werkzeug
import structlog
import sqlalchemy.sql
from pylti1p3.actions import Action as PyLTI1p3Action
from pylti1p3.lineitem import LineItem
from typing_extensions import Final, Literal
from pylti1p3.deployment import Deployment
from pylti1p3.oidc_login import OIDCLogin
from pylti1p3.tool_config import ToolConfAbstract
from pylti1p3.registration import Registration
from pylti1p3.message_launch import MessageLaunch
from pylti1p3.service_connector import ServiceConnector
from pylti1p3.assignments_grades import AssignmentsGradesService
from pylti1p3.deep_link_resource import DeepLinkResource

import flask
from cg_dt_utils import DatetimeWithTimezone

from . import claims
from ... import PsefFlask, models, helpers, signals, current_app
from .flask import (
    FlaskRequest, FlaskRedirect, FlaskCookieService, FlaskSessionService
)
from .roles import SystemRole
from ...cache import cache_within_request_make_key
from ...models import db
from ..abstract import AbstractLTIConnector
from ...exceptions import APICodes, APIException

logger = structlog.get_logger()

T = t.TypeVar('T')

if t.TYPE_CHECKING:
    from pylti1p3.message_launch import _JwtData, _LaunchData

NEEDED_AGS_SCOPES = [
    'https://purl.imsglobal.org/spec/lti-ags/scope/score',
    'https://purl.imsglobal.org/spec/lti-ags/scope/lineitem',
]

NEEDED_SCOPES = [
    *NEEDED_AGS_SCOPES,
    'https://purl.imsglobal.org/spec/lti-nrps/scope/contextmembership.readonly',
]


class CGAssignmentsGradesService(AssignmentsGradesService):
    def __init__(
        self, service_connector: ServiceConnector,
        assignment: 'models.Assignment'
    ):
        assert assignment.is_lti
        assert isinstance(assignment.lti_grade_service_data, dict)

        super().__init__(service_connector, assignment.lti_grade_service_data)
        self._assignment = assignment


class CGCustomClaims:
    @dataclasses.dataclass(frozen=True)
    class ClaimResult:
        username: str
        deadline: t.Optional[DatetimeWithTimezone]
        is_available: t.Optional[bool]
        resource_id: t.Optional[str]
        assignment_id: t.Optional[int]

    class _ReplacementVar:
        def __init__(self, name: str) -> None:
            self.name = name

    class _AbsoluteVar:
        def __init__(self, name: str) -> None:
            self.name = name

    @dataclasses.dataclass(frozen=True)
    class _Var:
        name: str
        opts: t.List[t.Union['CGCustomClaims._ReplacementVar',
                             'CGCustomClaims._AbsoluteVar']]
        required: bool

        def get_replacement_opts(
            self
        ) -> t.Iterable['CGCustomClaims._ReplacementVar']:
            for opt in self.opts:
                if isinstance(opt, CGCustomClaims._ReplacementVar):
                    yield opt

        def get_key(self, idx: int) -> str:
            return f'{self.name}_{idx}'

    _WANTED_VARS: Final = [
        _Var(
            'cg_username', [
                _ReplacementVar('$User.username'),
                _AbsoluteVar('lis_person_sourcedid')
            ], True
        ),
        _Var(
            'cg_deadline',
            [
                _ReplacementVar('$ResourceLink.submission.endDateTime'),
                _ReplacementVar('$Canvas.assignment.dueAt.iso8601')
            ],
            False,
        ),
        _Var(
            'cg_available_at',
            [_ReplacementVar('$ResourceLink.submission.startDateTime')],
            False,
        ),
        _Var(
            'cg_is_published',
            [_ReplacementVar('$Canvas.assignment.published')],
            False,
        ),
        _Var(
            'cg_resource_id',
            [_ReplacementVar('$ResourceLink.id')],
            False,
        )
    ]

    _VAR_LOOKUP: Final = {var.name: var for var in _WANTED_VARS}

    @classmethod
    def get_variable_claims_config(cls) -> t.Mapping[str, str]:
        res: t.Dict[str, str] = {}
        for var in cls._WANTED_VARS:
            for idx, opt in enumerate(var.get_replacement_opts()):
                res[var.get_key(idx)] = opt.name

        return res

    @classmethod
    def get_claim_keys(cls) -> t.Iterable[str]:
        yield from cls.get_variable_claims_config().keys()

    @classmethod
    def _get_claim(
        cls,
        var_name: str,
        custom_data: t.Mapping[str, str],
        base_data: t.Mapping[str, object],
        converter: t.Callable[[str], T],
    ) -> t.Optional[T]:
        var = cls._VAR_LOOKUP[var_name]

        for idx, opt in enumerate(var.opts):
            found_val: object

            if isinstance(opt, cls._ReplacementVar):
                found_val = custom_data.get(var.get_key(idx), opt.name)
            else:
                found_val = base_data.get(opt.name, opt.name)

            if isinstance(found_val, str) and found_val != opt.name:
                logger.info(
                    'Trying to parse claim',
                    found_value=found_val,
                    current_variable=var
                )
                return converter(found_val)

        if var.required:
            raise AssertionError(
                'Required variable {} was not found in {}'.format(
                    var_name, base_data
                )
            )
        return None

    @classmethod
    def get_custom_claim_data(
        cls,
        custom_claims: t.Mapping[str, str],
        base_data: t.Mapping[str, object],
    ) -> 'CGCustomClaims.ClaimResult':
        username = cls._get_claim('cg_username', custom_claims, base_data, str)
        # Username is a required var
        # TODO: Use an actual exception here
        assert username is not None, 'Required data not found'

        resource_id = cls._get_claim(
            'cg_resource_id', custom_claims, base_data, str
        )

        deadline = cls._get_claim(
            'cg_deadline', custom_claims, base_data,
            DatetimeWithTimezone.parse_isoformat
        )

        available_at = cls._get_claim(
            'cg_available_at', custom_claims, base_data,
            DatetimeWithTimezone.parse_isoformat
        )
        if available_at is None:
            is_available = cls._get_claim(
                'cg_is_published', custom_claims,
                base_data, lambda x: x == 'true'
            )
        else:
            is_available = DatetimeWithTimezone.utcnow() >= available_at

        assignment_id: t.Optional[int]
        try:
            assignment_id = int(custom_claims['cg_assignment_id'])
        except (TypeError, ValueError, KeyError):
            assignment_id = None

        return CGCustomClaims.ClaimResult(
            username=username,
            deadline=deadline,
            is_available=is_available,
            resource_id=resource_id,
            assignment_id=assignment_id,
        )


class CGDeepLinkResource(DeepLinkResource):
    def __init__(
        self, *, assignment: 'models.Assignment', add_params_to_url: bool
    ) -> None:
        super().__init__()
        self._assig = assignment

        self.set_type('ltiResourceLink')
        self.set_title(assignment.name)

        custom_params = {'cg_assignment_id': str(assignment.id)}
        self.set_custom_params(custom_params)

        url = current_app.config['EXTERNAL_URL'] + '/api/v1/lti1.3/launch'
        if add_params_to_url:
            url += '?' + urllib.parse.urlencode(custom_params)

        self.set_lineitem(
            LineItem().set_resource_id(str(assignment.id)
                                       ).set_score_maximum(10)
        )

        self.set_url(url)

    def to_dict(self) -> t.Dict[str, object]:
        res = super().to_dict()
        if self._assig.deadline is not None:
            res['submission'] = {
                'endDateTime': self._assig.deadline.isoformat(),
            }
            res['endDateTime'] = self._assig.deadline.isoformat()
        return res


def init_app(app: PsefFlask) -> None:
    pass


class LTIConfig(ToolConfAbstract[FlaskRequest]):
    def find_registration_by_issuer(
        self, iss: str, *args: None,
        **kwargs: t.Union[Literal['message_launch', 'oidc_login'],
                          FlaskRequest, '_LaunchData']
    ) -> t.Optional[Registration]:
        filters = [models.LTI1p3Provider.iss == iss]

        client_id: object = None
        action = kwargs.get('action')
        if action == 'message_launch':
            jwt_body = kwargs['jwt_body']
            assert isinstance(jwt_body, dict)
            aud = jwt_body['aud']
            client_id = aud[0] if isinstance(aud, list) else aud
        elif action == 'oidc_login':
            request = kwargs['request']
            assert isinstance(request, FlaskRequest)
            client_id = request.get_param('client_id')

        if isinstance(client_id, str):
            filters.append(models.LTI1p3Provider.client_id == client_id)

        return helpers.filter_single_or_404(
            models.LTI1p3Provider,
            *filters,
        ).get_registration()

    def find_deployment(
        self,
        iss: str,
        deployment_id: str,
        get_param: t.Callable[[str], object],
    ) -> t.Optional[Deployment]:
        return None


class FlaskMessageLaunch(
    AbstractLTIConnector,
    MessageLaunch[FlaskRequest, LTIConfig, FlaskSessionService,
                  FlaskCookieService]
):
    _provider: t.Optional['models.LTI1p3Provider'] = None

    def get_lms_name(self) -> str:
        return self.get_lti_provider().lms_name

    def set_user_role(self, user: 'models.User') -> None:
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

    def find_assignment(
        self,
        course: 'models.Course',
    ) -> 'models.MyQuery[models.Assignment]':

        query = course.get_assignments()
        custom_claim = self.get_custom_claims()

        if custom_claim.assignment_id is not None:
            return query.filter(
                models.Assignment.id == custom_claim.assignment_id
            )

        resource_id = custom_claim.resource_id
        if resource_id is None:
            launch_data = self.get_launch_data()
            resource_claim = launch_data.get(claims.RESOURCE, {})
            resource_id = resource_claim.get('id', None)

        if resource_id is None:
            return query.filter(sqlalchemy.sql.false())

        return query.filter(
            models.Assignment.is_visible,
            models.Assignment.lti_assignment_id == resource_id,
        )

    def get_assignment(
        self, user: 'models.User', course: 'models.Course'
    ) -> 'models.Assignment':
        launch_data = self.get_launch_data()
        resource_claim = launch_data[claims.RESOURCE]
        resource_id = resource_claim['id']
        custom_claim = self.get_custom_claims()

        assignment = self.find_assignment(course).one_or_none()
        logger.bind(assignment=assignment)

        if assignment is None:
            raise APIException(
                (
                    'The assignment was not found on CodeGrade, please'
                    ' initiate a DeepLink when creating an LTI Assignment.'
                ), f'The assignment "{resource_id}" was not found',
                APICodes.OBJECT_NOT_FOUND, 404
            )
        elif assignment.is_being_deep_linked:
            assignment.complete_deep_link()
            assignment.lti_assignment_id = resource_id
        elif assignment.lti_assignment_id != resource_id:
            raise APIException(
                (
                    'This LTI assignment is already connected to a different'
                    ' assignment on the LMS. When deep linking please only'
                    ' select an existing assignment if this assignment is not'
                    ' already connected to a different assignment in your LMS.'
                ), (
                    f'The assignment "{assignment.id}" is already connected to'
                    f' the resource id {assignment.lti_assignment_id}, however'
                    f' the launch was for the resource with id {resource_id}.'
                ), APICodes.OBJECT_NOT_FOUND, 404
            )

        assignment.lti_grade_service_data = launch_data[claims.GRADES]

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

    def set_user_course_role(
        self, user: 'models.User', course: 'models.Course'
    ) -> t.Optional[str]:
        assert course.course_lti_provider
        return course.course_lti_provider.maybe_add_user_to_course(
            user,
            self.get_launch_data()[claims.ROLES],
        )

    def _get_request_param(self, key: str) -> object:
        return self._request.get_param(key)

    @classmethod
    def from_request(cls, request: flask.Request) -> 'FlaskMessageLaunch':
        self = cls(
            FlaskRequest(request, force_post=True),
            LTIConfig(),
            FlaskSessionService(request),
            FlaskCookieService(request),
        )
        return self

    def get_lti_provider(self) -> 'models.LTI1p3Provider':
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
            missing: t.Iterable[str],
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
            missing: t.Iterable[str]
            if mapping:
                missing = [key for key in keys if key not in mapping]
            else:
                missing = keys

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

        if not self.is_deep_link_launch() and not self.has_nrps():
            raise get_exc(
                (
                    'It looks like the NamesRoles Provisioning service is not'
                    ' enabled for this LTI deployment, please check your'
                    ' configuration.'
                ),
                launch_data,
                claims.NAMESROLES,
            )

        # TODO: Check how handle these checks for deep linking
        # (i.e. brightspace)
        ags = launch_data.get(claims.GRADES, {})
        check_and_raise(
            (
                'It looks like the Assignments and Grades service is not'
                ' enabled for this LTI deployment, please check your'
                ' configuration'
            ),
            ags,
            'scope',
        )

        scopes = ags.get('scope', [])

        check_and_raise(
            (
                'We do not have the required permissions for passing back'
                ' grades and updating deadlines in the LMS, please check your'
                ' configuration'
            ),
            {s: True
             for s in scopes},
            *NEEDED_AGS_SCOPES,
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
        launch_data = self.get_launch_data()
        return CGCustomClaims.get_custom_claim_data(
            launch_data[claims.CUSTOM], launch_data
        )

    def ensure_lti_user(
        self
    ) -> t.Tuple['models.User', t.Optional[str], t.Optional[str]]:
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

    def get_course(self) -> 'models.Course':
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
        if claims.NAMESROLES in launch_data:
            course_lti_provider.names_roles_claim = launch_data[
                claims.NAMESROLES]

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
