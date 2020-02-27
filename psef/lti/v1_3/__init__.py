import copy
import typing as t
import dataclasses

import requests
import werkzeug
import structlog
import sqlalchemy.sql
from pylti1p3.lineitem import LineItem
from typing_extensions import Final
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
from ...models import AssignmentVisibilityState, db
from ..abstract import AbstractLTIConnector
from ...exceptions import APICodes, APIException

logger = structlog.get_logger()

T = t.TypeVar('T')

if t.TYPE_CHECKING:
    from pylti1p3.message_launch import _JwtData, _LaunchData


class CGAssignmentsGradesService(AssignmentsGradesService):
    def __init__(
        self, service_connector: ServiceConnector,
        assignment: models.Assignment
    ):
        assert assignment.is_lti
        assert isinstance(assignment.lti_grade_service_data, dict)

        super().__init__(service_connector, assignment.lti_grade_service_data)
        self._assignment = assignment

    def _make_cache_key(self) -> t.Tuple[int]:
        return (self._assignment.id, )

    @cache_within_request_make_key(_make_cache_key)
    def get_default_line_item(self) -> LineItem:
        return self.find_lineitem_by_tag(str(self._assignment.id))

    @cache_within_request_make_key(_make_cache_key)
    def get_lineitems(self: 'CGAssignmentsGradesService') -> list:
        return super().get_lineitems()

    def update_line_item(self, line_item: 'LineItem') -> 'LineItem':
        access_token = self._service_connector.get_access_token(
            self._service_data['scope']
        )
        url = line_item.get_id()
        json = {
            'label': line_item.get_label(),
            'scoreMaximum': line_item.get_score_maximum(),
            'submission': {
                'endDateTime': line_item.get_end_date_time(),
            }
        }

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/vnd.ims.lis.v2.lineitem+json',
            'Content-Type': 'application/vnd.ims.lis.v2.lineitem+json',
        }
        res = requests.put(url, headers=headers, json=json, verify=False)
        #res.raise_for_status()
        return LineItem(res.json())


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

    def __init__(self, assignment: models.Assignment) -> None:
        self._assig = assignment

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

    _WANTED_PERMA: t.List[
        t.Tuple[str, t.Callable[['CGCustomClaims'], str]]] = [
            ('cg_assig_id', lambda self: str(self._assig.id))
        ]

    def get_claims_config(self) -> t.Mapping[str, str]:
        res: t.Dict[str, str] = {}
        return {}
        for key, producer in self._WANTED_PERMA:
            res[key] = producer(self)

        return res

    @classmethod
    def get_claim_keys(cls) -> t.Iterable[str]:
        for var in cls._WANTED_VARS:
            for idx, _ in enumerate(var.get_replacement_opts()):
                yield var.get_key(idx)

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
            if isinstance(opt, cls._ReplacementVar):
                found_val = custom_data.get(var.get_key(idx), opt.name)
            else:
                found_val = base_data.get(opt.name, opt.name)

            if found_val != opt.name:
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
        launch_data: '_LaunchData',
        *,
        base_data: t.Mapping[str, object] = None,
    ) -> 'CGCustomClaims.ClaimResult':
        data = launch_data[claims.CUSTOM]
        if base_data is None:
            base_data = launch_data

        username = cls._get_claim('cg_username', data, base_data, str)
        # Username is a required var
        assert username is not None

        resource_id = cls._get_claim('cg_resource_id', data, base_data, str)

        deadline = cls._get_claim(
            'cg_deadline', data, base_data,
            DatetimeWithTimezone.parse_isoformat
        )

        available_at = cls._get_claim(
            'cg_available_at', data, base_data,
            DatetimeWithTimezone.parse_isoformat
        )
        if available_at is None:
            is_available = cls._get_claim(
                'cg_is_published', data, base_data, lambda x: x == 'true'
            )
        else:
            is_available = DatetimeWithTimezone.utcnow() >= available_at

        # The default value we set in the LMS for the cg_assignment_id is also
        # 'NONE'. So if it is 'NONE' the variable was not expanded.
        assignment_id_str = data.get('cg_assig_id', 'NONE')
        if assignment_id_str == 'NONE':
            assignment_id = None
        else:
            assignment_id = int(assignment_id_str)

        return CGCustomClaims.ClaimResult(
            username=username,
            deadline=deadline,
            is_available=is_available,
            assignment_id=assignment_id,
            resource_id=resource_id,
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
        self.set_lineitem(
            LineItem().set_tag(str(assignment.id)).set_score_maximum(10)
        )

    def to_dict(self) -> t.Dict[str, object]:
        res = super().to_dict()
        assert self._assig.deadline is not None
        res['submission'] = {
            'endDateTime': self._assig.deadline.isoformat(),
        }
        return res


def init_app(app: PsefFlask) -> None:
    pass


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

    def get_create_deep_link_assignment(self, course: models.Course
                                        ) -> t.Tuple[models.Assignment, bool]:
        assignment = self.find_assignment(course).one_or_none()
        if assignment is not None:
            return assignment, False

        return (
            models.Assignment(
                course=course,
                visibility_state=AssignmentVisibilityState.deep_linked,
                is_lti=True,
            ),
            True,
        )

    def find_assignment(
        self,
        course: models.Course,
    ) -> models.MyQuery[models.Assignment]:
        query = course.get_assignments()
        custom_claim = self.get_custom_claims()
        if custom_claim.resource_id is None:
            launch_data = self.get_launch_data()
            resource_claim = launch_data.get(claims.RESOURCE, {})
            resource_id = resource_claim.get('id', -1)
        else:
            resource_id = custom_claim.resource_id

        # For some reason some lmssen (looking at you blackboard) forget our
        # custom parameters after editing the assignment. In that case we want
        # to search using the `resource_id` as that should be available in that
        # case.
        if custom_claim.assignment_id is None:
            logger.info(
                (
                    'Custom cg_assig_id claim was not available, using'
                    ' resource_id'
                ),
                custom_claim=custom_claim,
                resource_id=resource_id,
                launch_data=self.get_launch_data(),
            )
            if resource_id is None:
                return query.filter(sqlalchemy.sql.false())
            return query.filter(
                models.Assignment.is_visible,
                models.Assignment.lti_assignment_id == resource_id,
            )
        else:
            return query.filter(
                models.Assignment.id == custom_claim.assignment_id,
            )

    def get_assignment(
        self, user: models.User, course: models.Course
    ) -> models.Assignment:
        launch_data = self.get_launch_data()
        resource_claim = launch_data[claims.RESOURCE]
        custom_claim = self.get_custom_claims()

        resource_id = resource_claim['id']

        assignment = self.find_assignment(course).one_or_none()
        logger.bind(assignment=assignment)

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
                missing = [key for key in keys if key not in mapping]
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
