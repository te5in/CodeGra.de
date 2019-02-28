"""This module contains the code used for all LTI functionality.

SPDX-License-Identifier: AGPL-3.0-only AND MIT

This entire file is licensed as AGPL-3.0-only, except for the code copied
from https://github.com/ucfopen/lti-template-flask-oauth-tokens which is
MIT licensed. This copied code is located between the ``# START OF MIT LICENSED
COPIED WORK #`` and the ``# END OF MIT LICENSED COPIED WORK #`` comment blocks.
"""
import abc
import enum
import typing as t
import datetime
import xml.etree.ElementTree
from urllib.parse import urlparse

import flask
import oauth2
import dateutil
import httplib2
import structlog
import flask_jwt_extended as flask_jwt
from mypy_extensions import TypedDict
from defusedxml.ElementTree import fromstring as defused_xml_fromstring

from dataclasses import dataclass

from . import (
    LTI_ROLE_LOOKUPS, app, auth, models, helpers, features, current_user
)
from .auth import _user_active
from .models import db
from .helpers import register
from .exceptions import APICodes, APIException

logger = structlog.get_logger()


def init_app(_: t.Any) -> None:
    pass


# We do this as defusedxml overrides some of these classes and doing an `import
# ... as ET` causes different definitions, which means that `ET.ParseError`
# cannot be excepted.
ET = xml.etree.ElementTree

LTI_NAMESPACES = {
    'xmlns': 'http://www.imsglobal.org/services/ltiv1p1/xsd/imsoms_v1p0'
}


@dataclass
class LTIProperty:
    """An LTI property.

    :ivar internal: The name the property should be names in the launch params.
    :ivar external: The external name of the property.
    """
    internal: str
    external: str


T_LTI = t.TypeVar('T_LTI', bound='LTI')  # pylint: disable=invalid-name

lti_classes: register.Register[str, t.Type['LTI']] = register.Register()


# TODO: This class has so many public methods as they are properties. A lot of
# them can be converted to private properties which should be done.
class LTI:  # pylint: disable=too-many-public-methods
    """The base LTI class.
    """

    @staticmethod
    def supports_lti_launch_as_result() -> bool:  # pragma: no cover
        """Does this LTI consumer support the ``ltiLaunchUrl`` as result field.
        """
        return False

    def __init__(
        self,
        params: t.Mapping[str, str],
        lti_provider: models.LTIProvider = None
    ) -> None:
        self.launch_params = params

        if lti_provider is not None:
            self.lti_provider = lti_provider
        else:
            lti_id = params['lti_provider_id']
            self.lti_provider = helpers.get_or_404(
                models.LTIProvider,
                lti_id,
            )

        self.key = self.lti_provider.key
        self.secret = self.lti_provider.secret

    @staticmethod
    def create_from_request(req: flask.Request) -> 'LTI':
        """Create an instance from a flask request.

        The request should have a ``form`` variable that has all the right
        parameters. So this request should be from an LTI launch.

        :param req: The request to create the LTI instance from.
        :returns: A fresh LTI instance.
        """
        params = req.form.copy()

        lti_provider = models.LTIProvider.query.filter_by(
            key=params['oauth_consumer_key'],
        ).first()
        if lti_provider is None:
            lti_provider = models.LTIProvider(key=params['oauth_consumer_key'])
            db.session.add(lti_provider)
            db.session.commit()

        params['lti_provider_id'] = lti_provider.id

        # This is semi sensitive information so it should not end up in the JWT
        # token.
        launch_params = {}
        for key, value in params.items():
            if not key.startswith('oauth'):
                launch_params[key] = value

        cls = lti_provider.lti_class
        self = cls(launch_params, lti_provider)
        launch_params['lti_class'] = lti_classes.get_key(cls)
        assert launch_params['lti_class'] is not None

        auth.ensure_valid_oauth(self.key, self.secret, req)

        return self

    @staticmethod
    def create_from_launch_params(params: t.Mapping[str, str]) -> 'LTI':
        """Create an instance from launch params.

        The params should have an ``lti_class`` key with the name of the class
        to be instantiated.

        :param params: The launch params to create the LTI instance from.
        :returns: A fresh LTI instance.
        """
        lms = params['lti_class']
        cls = lti_classes.get(lms)
        assert cls is not None
        return cls(params)

    @staticmethod
    def get_lti_properties() -> t.List[LTIProperty]:
        """All extension properties used by this LMS.

        :returns: The extension properties needed.
        """
        raise NotImplementedError

    @staticmethod
    def get_custom_extensions() -> str:
        """Get a string that will be used verbatim in the LTI xml.

        :returns: A string used as extension
        """
        raise NotImplementedError

    @staticmethod
    def supports_max_points() -> bool:
        """Determine whether this LMS supports changing the max points.

        :returns: A boolean indicating whether this LTI instance supports
            changing the max points.
        """
        return False

    @staticmethod
    def supports_deadline() -> bool:
        return False

    @staticmethod
    def supports_state_management() -> bool:
        return True

    @property
    def assignment_points_possible(self) -> float:
        """The amount of points possible for the launched assignment.
        """
        raise NotImplementedError

    @property
    def user_id(self) -> str:
        """The unique id of the current LTI user.
        """
        return self.launch_params['user_id']

    @property
    def user_email(self) -> str:
        """The email of the current LTI user.
        """
        return self.launch_params['lis_person_contact_email_primary']

    @property
    def full_name(self) -> str:
        """The name of the current LTI user.
        """
        return self.launch_params['lis_person_name_full']

    @property
    def username(self) -> str:  # pragma: no cover
        """The username of the current LTI user.
        """
        return self.launch_params['user_id']

    @property
    def course_id(self) -> str:  # pragma: no cover
        """The course id of the current LTI course.
        """
        return self.launch_params['context_id']

    @property
    def course_name(self) -> str:  # pragma: no cover
        """The name of the current LTI course.
        """
        return self.launch_params['context_title']

    @property
    def assignment_id(self) -> str:
        """The id of the current LTI assignment.
        """
        raise NotImplementedError

    @property
    def assignment_name(self) -> str:
        """The name of the current LTI assignment.
        """
        raise NotImplementedError

    @property
    def outcome_service_url(self) -> str:
        """The url used to passback grades to Canvas.
        """
        raise NotImplementedError

    def has_outcome_service_url(self) -> bool:
        """Check if the current LTI request has ``outcome_service_url`` field.

        This is not the case when launch LTI occurs for viewing a result.

        :returns: A boolean indicating if a ``sourcedid`` field was found.
        """
        raise NotImplementedError

    @property
    def result_sourcedid(self) -> str:
        """The sourcedid of the current user for the current assignment.
        """
        raise NotImplementedError

    @property
    def assignment_state(self) -> models._AssignmentStateEnum:  # pylint: disable=protected-access
        """The state of the current LTI assignment.
        """
        raise NotImplementedError

    @property
    def roles(self) -> t.Iterable[str]:
        """The normalized roles of the current LTI user.
        """
        raise NotImplementedError

    def get_assignment_deadline(self, default: datetime.datetime = None
                                ) -> t.Optional[datetime.datetime]:
        """Get the deadline of the current LTI assignment.

        :param default: The value to be returned of the assignment has no
            deadline. If ``default.__bool__`` is ``False`` the current date
            plus 365 days is used.
        :returns: The deadline of the assignment as a datetime.
        """
        raise NotImplementedError

    def ensure_lti_user(
        self
    ) -> t.Tuple[models.User, t.Optional[str], t.Optional[str]]:
        """Make sure the current LTI user is logged in as a psef user.

        This is done by first checking if we know a user with the current LTI
        user_id, if this is the case this is the user we log in and return.

        Otherwise we check if a user is logged in and this user has no LTI
        user_id, if this is the case we link the current LTI user_id to the
        current logged in user and return this user.

        Otherwise we create a new user and link this user to current LTI
        user_id.

        :returns: A tuple containing the items in order: the user found as
            described above, optionally a new token for the user to login with,
            optionally the updated email of the user as a string, this is
            ``None`` if the email was not updated.
        """
        is_logged_in = _user_active(current_user)
        token = None
        user = None

        lti_user = models.User.query.filter_by(lti_user_id=self.user_id
                                               ).first()

        if is_logged_in and current_user.lti_user_id == self.user_id:
            # The currently logged in user is now using LTI
            user = current_user

        elif lti_user is not None:
            # LTI users are used before the current logged user.
            token = flask_jwt.create_access_token(
                identity=lti_user.id,
                fresh=True,
            )
            user = lti_user
        elif is_logged_in and current_user.lti_user_id is None:
            # TODO show some sort of screen if this linking is wanted
            current_user.lti_user_id = self.user_id
            db.session.flush()
            user = current_user
        else:
            # New LTI user id is found and no user is logged in or the current
            # user has a different LTI user id. A new user is created and
            # logged in.
            i = 0

            def _get_username() -> str:
                return self.username + (f' ({i})' if i > 0 else '')

            while db.session.query(
                models.User.query.filter_by(username=_get_username()).exists()
            ).scalar():  # pragma: no cover
                i += 1

            user = models.User(
                lti_user_id=self.user_id,
                name=self.full_name,
                email=self.user_email,
                active=True,
                password=None,
                username=_get_username(),
            )
            db.session.add(user)
            db.session.flush()

            token = flask_jwt.create_access_token(
                identity=user.id,
                fresh=True,
            )

        assert user is not None

        updated_email = None
        if user.reset_email_on_lti:
            user.email = self.user_email
            updated_email = self.user_email
            user.reset_email_on_lti = False

        return user, token, updated_email

    def get_course(self) -> models.Course:
        """Get the current LTI course as a psef course.
        """
        course = models.Course.query.filter_by(lti_course_id=self.course_id
                                               ).first()
        if course is None:
            course = models.Course(
                name=self.course_name, lti_course_id=self.course_id
            )
            db.session.add(course)

        if course.name != self.course_name:
            logger.info(
                'Course changed name',
                old_name=course.name,
                new_name=self.course_name
            )
            course.name = self.course_name

        course.lti_provider = self.lti_provider
        db.session.flush()

        return course

    def get_assignment(
        self, user: models.User, course: models.Course
    ) -> models.Assignment:
        """Get the current LTI assignment as a psef assignment.
        """
        assignment = models.Assignment.query.filter_by(
            lti_assignment_id=self.assignment_id,
        ).first()
        if assignment is None:
            assignment = models.Assignment(
                name=self.assignment_name,
                state=self.assignment_state,
                course=course,
                deadline=self.get_assignment_deadline(),
                lti_assignment_id=self.assignment_id,
                description=''
            )
            db.session.add(assignment)
            db.session.flush()

        if assignment.course != course:  # pragma: no cover
            logger.warning(
                'Assignment changed course!',
                assignment=assignment,
                course=course,
            )
            assignment.course = course

        if self.has_result_sourcedid():
            if assignment.id in user.assignment_results:
                user.assignment_results[assignment.id
                                        ].sourcedid = self.result_sourcedid
            else:
                assig_res = models.AssignmentResult(
                    sourcedid=self.result_sourcedid,
                    user_id=user.id,
                    assignment_id=assignment.id
                )
                db.session.add(assig_res)

        if self.has_assignment_points_possible():
            assignment.lti_points_possible = self.assignment_points_possible

        if self.has_outcome_service_url():
            assignment.lti_outcome_service_url = self.outcome_service_url

        if not assignment.is_done:
            assignment.state = self.assignment_state

        if assignment.name != self.assignment_name:
            logger.info(
                'Assignment changed name',
                old_name=assignment.name,
                new_name=self.assignment_name
            )
            assignment.name = self.assignment_name

        assignment.deadline = self.get_assignment_deadline(
            default=assignment.deadline
        )

        db.session.flush()

        return assignment

    def set_user_role(self, user: models.User) -> None:
        """Set the role of the given user if the user has no role.

        The role is determined according to :py:data:`.LTI_ROLE_LOOKUPS`.

        .. note::
            If the role could not be matched the ``DEFAULT_ROLE`` configured
            in the config of the app is used.

        :param models.User user: The user to set the role for.
        :returns: Nothing
        :rtype: None
        """
        if user.role is None:
            for role in self.roles:
                if role not in LTI_ROLE_LOOKUPS:
                    continue
                role_lookup = LTI_ROLE_LOOKUPS[role]
                if role_lookup['course_role']:  # This is a course role
                    continue
                user.role = models.Role.query.filter_by(
                    name=role_lookup['role']
                ).one()
                return
            user.role = models.Role.query.filter_by(
                name=app.config['DEFAULT_ROLE']
            ).one()

    def set_user_course_role(self, user: models.User,
                             course: models.Course) -> t.Union[str, bool]:
        """Set the course role for the given course and user if there is no
        such role just yet.

        The mapping is done using :py:data:`.LTI_ROLE_LOOKUPS`. If no role
        could be found a new role is created with the default permissions.

        :param models.User user: The user to set the course role  for.
        :param models.Course course: The course to connect to user to.
        :returns: True if a new role was created.
        """
        if course.id not in user.courses:
            unkown_roles = []
            for role in self.roles:
                if role not in LTI_ROLE_LOOKUPS:
                    unkown_roles.append(role)
                    continue
                role_lookup = LTI_ROLE_LOOKUPS[role]
                if not role_lookup['course_role']:  # This is not a course role
                    continue

                crole = models.CourseRole.query.filter_by(
                    course_id=course.id, name=role_lookup['role']
                ).one()
                user.courses[course.id] = crole
                return False

            if not features.has_feature(features.Feature.AUTOMATIC_LTI_ROLE):
                raise APIException(
                    'The given LTI role was not valid found, please '
                    'ask your instructor or site admin.',
                    f'No role in "{list(self.roles)}" is a known LTI role',
                    APICodes.INVALID_STATE, 400
                )

            # Add a new course role
            new_created: t.Union[bool, str] = False
            new_role = (unkown_roles + ['New LTI Role'])[0]
            existing_role = models.CourseRole.query.filter_by(
                course_id=course.id, name=new_role
            ).first()
            if existing_role is None:
                existing_role = models.CourseRole(course=course, name=new_role)
                db.session.add(existing_role)
                new_created = new_role
            user.courses[course.id] = existing_role
            return new_created
        return False

    def has_result_sourcedid(self) -> bool:
        """Check if the current LTI request has a ``sourcedid`` field.

        :returns: A boolean indicating if a ``sourcedid`` field was found.
        """
        raise NotImplementedError

    def has_assignment_points_possible(self) -> bool:
        """Check if the current LTI request has a ``pointsPossible`` field.

        :returns: A boolean indicating if a ``pointsPossible`` field was found.
        """
        raise NotImplementedError

    @classmethod
    def generate_xml(cls) -> str:
        """Generate a config XML for this LTI consumer.
        """
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def passback_grade(
        cls: t.Type[T_LTI],
        *,
        key: str,
        secret: str,
        grade: t.Union[float, None, int],
        initial: bool,
        service_url: str,
        sourcedid: str,
        lti_points_possible: t.Optional[float],
        submission: models.Work,
        host: str,
    ) -> None:
        """Do a LTI grade passback.

        :param key: The oauth key to use.
        :param secret: The oauth secret to use.
        :param grade: The grade to pass back, between 0 and
            10. If it is `None` the grade will be deleted, if it is a ``bool``
            no grade information will be send.
        :param service_url: The url used for grade passback.
        :param sourcedid: The ``sourcedid`` used in the grade passback.
        :param lti_points_possible: The maximum amount of points possible for
            the assignment we are passing back as reported by the LMS during
            launch.
        :param host: The host of this CodeGrade instance.
        :returns: The response of the LTI consumer.
        """
        raise NotImplementedError

    @classmethod
    def _passback_grade(
        cls: t.Type[T_LTI],
        *,
        key: str,
        secret: str,
        grade: t.Union[float, int, None],
        initial: bool,
        service_url: str,
        sourcedid: str,
        lti_points_possible: t.Optional[float],
        submission: models.Work,
        use_submission_details: bool,
        url: str,
    ) -> None:
        logger.info(
            'Doing LTI grade passback',
            consumer_key=key,
            consumer_secret=secret,
            lti_outcome_service_url=service_url,
            url=url,
            grade=grade,
            initial=initial,
            use_submission_details=use_submission_details,
        )
        lti_operation: LTIOperation
        submission_details: SubmissionDetails = {}
        if use_submission_details:
            submission_details['submittedAt'] = submission.created_at.replace(
                tzinfo=datetime.timezone.utc
            ).isoformat()

        data_type = (
            LTIResultDataType.lti_launch_url
            if cls.supports_lti_launch_as_result() else LTIResultDataType.url
        )

        if initial:
            lti_operation = LTIInitalReplaceResultOperation(
                data_type=data_type,
                data_value=url,
                submission_details=submission_details,
            )
        elif grade is None:
            lti_operation = LTIDeleteResultOperation()
        elif grade > 10:
            assert lti_points_possible is not None
            lti_operation = LTIRawReplaceResultOperation(
                data_type=data_type,
                data_value=url,
                grade=str((grade / 10) * lti_points_possible),
                submission_details=submission_details,
            )
        else:
            lti_operation = LTINormalReplaceResultOperation(
                data_type=data_type,
                data_value=url,
                grade=str((grade / 10)),
                submission_details=submission_details,
            )

        OutcomeRequest(
            consumer_key=key,
            consumer_secret=secret,
            lis_outcome_service_url=service_url,
            lis_result_sourcedid=sourcedid,
            lti_operation=lti_operation,
            message_identifier=str(submission.id),
        ).post_outcome_request()


@lti_classes.register('Canvas')
class CanvasLTI(LTI):
    """The LTI class used for the Canvas LMS.
    """

    @staticmethod
    def supports_lti_launch_as_result() -> bool:
        return True

    @staticmethod
    def get_lti_properties() -> t.List[LTIProperty]:
        """All extension properties used by Canvas.

        :returns: The extension properties needed.
        """
        return [
            LTIProperty(
                internal='custom_canvas_course_name',
                external='$Canvas.course.name'
            ),
            LTIProperty(
                internal='custom_canvas_course_id',
                external='$Canvas.course.id'
            ),
            LTIProperty(
                internal='custom_canvas_assignment_id',
                external='$Canvas.assignment.id'
            ),
            LTIProperty(
                internal='custom_canvas_assignment_title',
                external='$Canvas.assignment.title'
            ),
            LTIProperty(
                internal='custom_canvas_assignment_due_at',
                external='$Canvas.assignment.dueAt.iso8601'
            ),
            LTIProperty(
                internal='custom_canvas_assignment_published',
                external='$Canvas.assignment.published'
            ),
            LTIProperty(
                internal='custom_canvas_points_possible',
                external='$Canvas.assignment.pointsPossible'
            ),
        ]

    @staticmethod
    def get_custom_extensions() -> str:
        """Get the custom extension use by Canvas.

        :returns: The extension used by canvas.
        """
        return """
    <blti:extensions platform="canvas.instructure.com">
      <lticm:property name="tool_id">codegrade</lticm:property>
      <lticm:property name="privacy_level">public</lticm:property>
      <lticm:property name="domain">{}</lticm:property>
    </blti:extensions>
        """.format(urlparse(app.config['EXTERNAL_URL']).netloc)

    @staticmethod
    def supports_max_points() -> bool:
        return True

    @staticmethod
    def supports_deadline() -> bool:
        return True

    @staticmethod
    def supports_state_management() -> bool:
        return True

    def has_assignment_points_possible(self) -> bool:
        return 'custom_canvas_points_possible' in self.launch_params

    @property
    def assignment_points_possible(self) -> float:
        """The amount of points possible for the launched assignment.
        """
        return float(self.launch_params['custom_canvas_points_possible'])

    @property
    def username(self) -> str:
        return self.launch_params['custom_canvas_user_login_id']

    @property
    def course_name(self) -> str:
        return self.launch_params['custom_canvas_course_name']

    @property
    def course_id(self) -> str:
        return self.launch_params['custom_canvas_course_id']

    @property
    def assignment_id(self) -> str:
        return self.launch_params['custom_canvas_assignment_id']

    @property
    def assignment_name(self) -> str:
        return self.launch_params['custom_canvas_assignment_title']

    @property
    def outcome_service_url(self) -> str:
        return self.launch_params['lis_outcome_service_url']

    def has_outcome_service_url(self) -> bool:
        return 'lis_outcome_service_url' in self.launch_params

    @property
    def result_sourcedid(self) -> str:
        return self.launch_params['lis_result_sourcedid']

    def has_result_sourcedid(self) -> bool:
        return 'lis_result_sourcedid' in self.launch_params

    @classmethod
    def generate_xml(cls) -> str:
        """Generate a config XML for this LTI consumer.
        """
        return flask.render_template(
            'lti_canvas_config.j2',
            external_url=app.config['EXTERNAL_URL'],
            properties=cls.get_lti_properties(),
            custom_extensions=cls.get_custom_extensions(),
        )

    @property
    def assignment_state(self) -> models._AssignmentStateEnum:
        # pylint: disable=protected-access
        if self.launch_params['custom_canvas_assignment_published'] == 'true':
            return models._AssignmentStateEnum.open
        else:
            return models._AssignmentStateEnum.hidden

    @property
    def roles(self) -> t.Iterable[str]:
        for role in self.launch_params['roles'].split(','):
            yield role.split('/')[-1].lower()

    def get_assignment_deadline(self, default: datetime.datetime = None
                                ) -> t.Optional[datetime.datetime]:
        try:
            deadline = dateutil.parser.parse(
                self.launch_params['custom_canvas_assignment_due_at']
            )
            deadline = deadline.astimezone(datetime.timezone.utc)
            return deadline.replace(tzinfo=None)
        except (KeyError, ValueError, OverflowError):
            return (
                datetime.datetime.utcnow() + datetime.timedelta(days=365)
            ) if default is None else default

    @classmethod
    def passback_grade(
        cls: t.Type[T_LTI],
        *,
        key: str,
        secret: str,
        grade: t.Union[float, None, int],
        initial: bool,
        service_url: str,
        sourcedid: str,
        lti_points_possible: t.Optional[float],
        submission: models.Work,
        host: str,
    ) -> None:
        redirect = (
            '/courses/{course_id}'
            '/assignments/{assig_id}'
            '/submissions/{sub_id}?inLTI=true'
        ).format(
            course_id=submission.assignment.course_id,
            assig_id=submission.assignment_id,
            sub_id=submission.id,
        )
        # Namespacing this get parameter is important as Canvas duplicates all
        # get parameters in the body. This makes sure we won't override actual
        # launch parameters. Also the url doesn't need to be quoted, as canvas
        # does this for us.
        url = f'{host}/api/v1/lti/launch/1?codegrade_redirect={redirect}'
        super()._passback_grade(
            key=key,
            secret=secret,
            grade=grade,
            initial=initial,
            service_url=service_url,
            sourcedid=sourcedid,
            lti_points_possible=lti_points_possible,
            submission=submission,
            use_submission_details=True,
            url=url,
        )


@lti_classes.register('Blackboard')
class BlackboardLTI(LTI):
    """The LTI class used for the Blackboard LMS.
    """

    @staticmethod
    def supports_lti_launch_as_result() -> bool:
        return False

    @staticmethod
    def get_lti_properties() -> t.List[LTIProperty]:
        return []

    @staticmethod
    def get_custom_extensions() -> str:
        return ''

    def has_assignment_points_possible(self) -> bool:
        return False

    @property
    def username(self) -> str:
        return self.launch_params['lis_person_sourcedid']

    @property
    def course_id(self) -> str:
        return self.launch_params['context_id']

    @property
    def course_name(self) -> str:
        return self.launch_params['context_title']

    @property
    def assignment_id(self) -> str:
        return self.launch_params['resource_link_id']

    @property
    def assignment_name(self) -> str:
        return self.launch_params['resource_link_title']

    @property
    def outcome_service_url(self) -> str:
        return self.launch_params['lis_outcome_service_url']

    def has_outcome_service_url(self) -> bool:
        return 'lis_outcome_service_url' in self.launch_params

    @property
    def result_sourcedid(self) -> str:
        return self.launch_params['lis_result_sourcedid']

    def has_result_sourcedid(self) -> bool:
        return 'lis_result_sourcedid' in self.launch_params

    @property
    def assignment_state(self) -> models._AssignmentStateEnum:
        return models._AssignmentStateEnum.open

    @property
    def roles(self) -> t.Iterable[str]:
        for role in self.launch_params['roles'].split(','):
            yield role.split('/')[-1].lower()

    def get_assignment_deadline(self, default: datetime.datetime = None
                                ) -> t.Optional[datetime.datetime]:
        return default

    @classmethod
    def passback_grade(
        cls: t.Type[T_LTI],
        *,
        key: str,
        secret: str,
        grade: t.Union[float, None, int],
        initial: bool,
        service_url: str,
        sourcedid: str,
        lti_points_possible: t.Optional[float],
        submission: models.Work,
        host: str,
    ) -> None:
        redirect = (
            '/courses/{course_id}'
            '/assignments/{assig_id}'
            '/submissions/{sub_id}?inLTI=true'
        ).format(
            course_id=submission.assignment.course_id,
            assig_id=submission.assignment_id,
            sub_id=submission.id,
        )
        # TODO: Review this...
        # Namespacing this get parameter is important as Canvas duplicates all
        # get parameters in the body. This makes sure we won't override actual
        # launch parameters. Also the url doesn't need to be quoted, as canvas
        # does this for us.
        url = f'{host}/api/v1/lti/launch/1?codegrade_redirect={redirect}'
        super()._passback_grade(
            key=key,
            secret=secret,
            grade=grade,
            initial=initial,
            service_url=service_url,
            sourcedid=sourcedid,
            lti_points_possible=lti_points_possible,
            submission=submission,
            use_submission_details=True,
            url=url,
        )


#####################################
# START OF MIT LICENSED COPIED WORK #
#####################################

# This part is largely copied from https://github.com/tophatmonocle/ims_lti_py
# and MIT licensed, see below for the entire license.

# The MIT License (MIT)
#
# Copyright (c) 2017 University of Central Florida - Center for Distributed
# Learning
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


@enum.unique
class LTIResultDataType(enum.Enum):
    """All possible result data options for an LTI replaceResult request.
    """
    text = 'text'
    url = 'url'
    lti_launch_url = 'ltiLaunchUrl'


class LTIOperation(abc.ABC):
    """Base class representing a LTI operation.
    """

    @property
    @abc.abstractmethod
    def request_type(self) -> str:
        """Get the name of this operation as required in the LTI xml.
        """
        raise NotImplementedError


class LTIDeleteResultOperation(LTIOperation):
    """A delete result LTI operation.

    This operation deletes the result at canvas.
    """
    request_type = 'deleteResultRequest'


SubmissionDetails = TypedDict(  # pylint: disable=invalid-name
    'SubmissionDetails', {'submittedAt': str}, total=False
)


@dataclass
class LTIReplaceResultBaseOperation(LTIOperation, abc.ABC):
    """The base replaceResult LTI operation.
    """
    request_type = 'replaceResultRequest'

    data_type: LTIResultDataType
    data_value: str

    submission_details: SubmissionDetails


@dataclass
class LTINormalReplaceResultOperation(LTIReplaceResultBaseOperation):
    """A normal replaceResult with a grade that is in [0, 1]
    """
    grade: str


@dataclass
class LTIRawReplaceResultOperation(LTIReplaceResultBaseOperation):
    """A raw replaceResult with a grade that represents the amount of points a
    user got for the assignment.

    .. note:: This is currently only supported by Canvas.
    """
    grade: str


@dataclass
class LTIInitalReplaceResultOperation(LTIReplaceResultBaseOperation):
    """An initial replaceResult operation, which doens't provide a grade.
    """


class OutcomeRequest:
    """Class for generating LTI Outcome Requests.

    Outcome Request documentation:
        http://www.imsglobal.org/LTI/v1p1/ltiIMGv1p1.html#_Toc319560472
    """

    def __init__(
        self,
        *,
        lis_outcome_service_url: str,
        lis_result_sourcedid: str,
        consumer_key: str,
        consumer_secret: str,
        lti_operation: LTIOperation,
        message_identifier: str,
    ) -> None:
        self.lis_outcome_service_url = lis_outcome_service_url
        self.lis_result_sourcedid = lis_result_sourcedid
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.lti_operation = lti_operation
        self.message_identifier = message_identifier

    def post_outcome_request(self) -> 'OutcomeResponse':
        """Send this ``OutcomeRequest`` to the LTI provider.

        :returns: The parsed response from the provider.
        """
        log = logger.bind(
            operation=self.lti_operation,
            lti_request_message_identifier=self.message_identifier
        )
        log.info('Posting outcome request')

        consumer = oauth2.Consumer(
            key=self.consumer_key, secret=self.consumer_secret
        )

        client = oauth2.Client(consumer)

        # monkeypatch the _normalize function to ensures that the
        # ``Authorization`` header is NOT lower cased
        normalize = httplib2.Http._normalize_headers  # pylint: disable=protected-access

        def __my_normalize(
            self: t.Any, headers: t.Sequence
        ) -> t.Sequence:  # pragma: no cover
            ret = normalize(self, headers)
            if 'authorization' in ret:
                ret['Authorization'] = ret.pop('authorization')
            return ret

        httplib2.Http._normalize_headers = __my_normalize  # pylint: disable=protected-access
        monkey_patch_function = normalize

        response: httplib2.Response
        content: str
        passback_body = self.__generate_request_xml()
        log.info('Doing passback request', body=passback_body)
        response, content = client.request(
            uri=self.lis_outcome_service_url,
            method='POST',
            body=passback_body,
            headers={'Content-Type': 'application/xml'},
        )

        # Restore original function
        httplib2.Http._normalize_headers = monkey_patch_function  # pylint: disable=protected-access

        log = log.bind(
            response=response,
            response_body=content,
        )
        log.info('Posted outcome request')

        outcome = OutcomeResponse(content)

        log.bind(
            lti_response_message_identifier=outcome.message_identifier,
            lti_response_ref_message_identifier=outcome.message_ref_identifier,
            lti_code_major=outcome.code_major,
            lti_severity=outcome.severity,
            lti_description=outcome.description,
        )

        if outcome.message_ref_identifier != self.message_identifier:
            log.error('Received wrong "message_ref_identifier" in request')

        if outcome.is_failure:  # pragma: no cover
            log.error('Posting outcome failed')
        elif outcome.has_warning:  # pragma: no cover
            log.warning('Posting outcome had a warning')
        else:
            log.info('Posting outcome was successful')

        log.try_unbind(
            'response', 'response_body', 'operation', 'lti_code_major',
            'lti_severity', 'lti_description', 'lti_request_message_identifier'
            'lti_request_message_identifier',
            'lti_response_ref_message_identifier'
        )

        return outcome

    def __generate_request_xml(self) -> bytes:
        """Generate an xml that can be used to perform an outcome request.

        :returns: The xml as a bytestring.
        """
        root = ET.Element(
            'imsx_POXEnvelopeRequest', xmlns=LTI_NAMESPACES['xmlns']
        )

        header = ET.SubElement(root, 'imsx_POXHeader')
        header_info = ET.SubElement(header, 'imsx_POXRequestHeaderInfo')
        version = ET.SubElement(header_info, 'imsx_version')
        version.text = 'V1.0'
        message_identifier = ET.SubElement(
            header_info, 'imsx_messageIdentifier'
        )
        message_identifier.text = self.message_identifier
        body = ET.SubElement(root, 'imsx_POXBody')
        request = ET.SubElement(body, self.lti_operation.request_type)
        record = ET.SubElement(request, 'resultRecord')

        guid = ET.SubElement(record, 'sourcedGUID')

        sourcedid = ET.SubElement(guid, 'sourcedId')
        sourcedid.text = self.lis_result_sourcedid

        if isinstance(self.lti_operation, LTIReplaceResultBaseOperation):
            result = ET.SubElement(record, 'result')

            if isinstance(
                self.lti_operation,
                (
                    LTINormalReplaceResultOperation,
                    LTIRawReplaceResultOperation
                )
            ):
                grade = self.lti_operation.grade

                if isinstance(
                    self.lti_operation, LTIRawReplaceResultOperation
                ):
                    result_score = ET.SubElement(result, 'resultTotalScore')
                else:
                    result_score = ET.SubElement(result, 'resultScore')

                language = ET.SubElement(result_score, 'language')
                language.text = 'en'
                text_string = ET.SubElement(result_score, 'textString')
                text_string.text = grade

            result_data = ET.SubElement(result, 'resultData')
            result_data_el = ET.SubElement(
                result_data, self.lti_operation.data_type.value
            )
            result_data_el.text = self.lti_operation.data_value

            if self.lti_operation.submission_details:
                details_el = ET.SubElement(request, 'submissionDetails')
                for key, value in self.lti_operation.submission_details.items(
                ):
                    sub_details_el = ET.SubElement(details_el, key)
                    sub_details_el.text = str(value)

        return ET.tostring(root, encoding='utf-8')


class OutcomeResponse:
    """This class consumes LTI Outcome Responses.

    Response documentation:
        http://www.imsglobal.org/LTI/v1p1/ltiIMGv1p1.html#_Toc319560472

    Error code documentation:
        http://www.imsglobal.org/gws/gwsv1p0/imsgws_baseProfv1p0.html#1639667

    >>> import doctest
    >>> import os
    >>> doctest.ELLIPSIS_MARKER = '-etc-'
    >>> get_file = lambda name: open(
    ... os.path.join(
    ...   os.path.dirname(__file__),
    ...   '..',
    ...   'test_data',
    ...   'example_strings',
    ...   name,
    ... )).read()

    >>> res = OutcomeResponse(get_file('invalid_xml.xml'))
    -etc-
    >>> res.code_major, res.severity, res.description
    ('failure', 'error', 'unknown error')
    >>> res.is_success, res.is_failure, res.has_warning
    (False, True, False)

    >>> res = OutcomeResponse(get_file('invalid_replace_result.xml'))
    -etc-
    >>> res.code_major, res.severity, res.description
    ('failure', 'error', 'unknown error')
    >>> res.is_success, res.is_failure, res.has_warning
    (False, True, False)

    >>> res = OutcomeResponse(get_file('valid_replace_result.xml'))
    >>> (
    ...   res.code_major,
    ...   res.severity,
    ...   res.description,
    ...   res.message_identifier,
    ...   res.message_ref_identifier,
    ... )
    ('success', 'status', 'Score for 3124567 is now 0.92', '4560', '999999123')
    >>> res.is_success, res.is_failure, res.has_warning
    (True, False, False)
    """

    def __init__(
        self,
        input_xml: str,
    ) -> None:
        self.message_identifier: t.Optional[str] = None

        self.code_major: t.Optional[str] = None
        self.severity: t.Optional[str] = None
        self.description: t.Optional[str] = None
        self.operation: t.Optional[str] = None
        self.message_ref_identifier: t.Optional[str] = None

        self.__process_xml(input_xml)

    @property
    def is_success(self) -> bool:
        """Check if a response indicated a success.

        :returns: ``True`` if the response indicated a success.
        """
        return self.code_major == 'success'

    @property
    def is_failure(self) -> bool:
        """Check if a response indicated a failure.

        :returns: ``True`` if the response indicated a failure.
        """
        return self.code_major == 'failure'

    @property
    def has_warning(self) -> bool:
        """Check if a response had a warning

        :returns: ``True`` if the response had a warning
        """
        return self.severity == 'warning'

    def __process_xml(self, input_xml: str) -> None:
        """Parse OutcomeResponse data form XML.

        :param xml: The xml to parse.
        :returns: Nothing
        """

        class WrongValueException(ValueError):
            pass

        def get_node(root: ET.Element, path: str) -> ET.Element:
            node = root.find(path, namespaces=LTI_NAMESPACES)
            if node is None:
                raise WrongValueException(
                    'Could not find path', root, path.split('/')
                )
            return node

        def get_text(root: ET.Element, path: str) -> t.Optional[str]:
            return get_node(root, path).text

        try:
            root: ET.Element = defused_xml_fromstring(input_xml)

            # Get message idenifier from header info
            self.message_identifier = get_text(
                root,
                (
                    'xmlns:imsx_POXHeader/'
                    'xmlns:imsx_POXResponseHeaderInfo/'
                    'xmlns:imsx_messageIdentifier'
                ),
            )

            status_node = get_node(
                root,
                (
                    'xmlns:imsx_POXHeader/'
                    'xmlns:imsx_POXResponseHeaderInfo/'
                    'xmlns:imsx_statusInfo'
                ),
            )

            # Get status parameters from header info status
            self.code_major = get_text(status_node, 'xmlns:imsx_codeMajor')
            self.severity = get_text(status_node, 'xmlns:imsx_severity')
            self.description = get_text(status_node, 'xmlns:imsx_description')
            self.message_ref_identifier = get_text(
                status_node, 'xmlns:imsx_messageRefIdentifier'
            )
            self.operation = get_text(
                status_node, 'xmlns:imsx_operationRefIdentifier'
            )
        except (WrongValueException, ET.ParseError):
            logger.error(
                'Broken xml received',
                xml_received=xml,
                exc_info=True,
            )
            self.code_major = 'failure'
            self.severity = 'error'
            self.description = 'unknown error'


###################################
# END OF MIT LICENSED COPIED WORK #
###################################
