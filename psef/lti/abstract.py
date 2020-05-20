import abc
import typing as t

import structlog
from mypy_extensions import TypedDict
from typing_extensions import Literal

from .. import auth, models
from ..exceptions import APICodes, APIException

logger = structlog.get_logger()


class LTILaunchData(TypedDict):
    assignment: t.Optional['models.Assignment']
    custom_lms_name: str
    new_role_created: t.Optional[str]
    access_token: t.Optional[str]
    updated_email: t.Optional[str]
    type: Literal['normal_result']


class AbstractLTIConnector(abc.ABC):
    @abc.abstractmethod
    def ensure_lti_user(
        self
    ) -> t.Tuple['models.User', t.Optional[str], t.Optional[str]]:
        """Make sure the current LTI user is logged in as a CodeGrade user.

        :returns: A tuple containing the items in order: A CodeGrade user,
            optionally a new token for the user to login with, optionally the
            updated email of the user as a string, this should be ``None`` if
            the email was not updated.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_course(self) -> 'models.Course':
        """Get the current LTI course as a CodeGrade course.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_assignment(
        self, user: 'models.User', course: 'models.Course'
    ) -> 'models.Assignment':
        """Get the current LTI assignment as a CodeGrade assignment.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def set_user_role(self, user: 'models.User') -> None:
        """Set the role of the given user if the user has no role.

        :param user: The user to set the role for.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def set_user_course_role(
        self, user: 'models.User', course: 'models.Course'
    ) -> t.Optional[str]:
        """Set the course role for the given course and user if there is no
        such role just yet.

        :param user: The user to set the course role for.
        :param course: The course to connect to user to.
        :returns: The name of the new role created, or ``None`` if no role was
            created.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_lms_name(self) -> str:
        """Get the name of the LMS that does the LTI launch.
        """
        raise NotImplementedError

    def do_second_step_of_lti_launch(self) -> LTILaunchData:
        try:
            user, new_token, updated_email = self.ensure_lti_user()
            auth.set_current_user(user)

            course = self.get_course()
            logger.bind(course=course)
            assig = self.get_assignment(user, course)
            logger.bind(assignment=assig)

            if assig.visibility_state.is_deleted:
                raise APIException(
                    'The launched assignment has been deleted on CodeGrade.',
                    f'The assignment "{assig.id}" has been deleted',
                    APICodes.OBJECT_NOT_FOUND, 404
                )

            self.set_user_role(user)
            new_role_created = self.set_user_course_role(user, course)

            models.db.session.commit()

            return LTILaunchData(
                assignment=assig,
                new_role_created=new_role_created,
                custom_lms_name=self.get_lms_name(),
                updated_email=updated_email,
                access_token=new_token,
                type='normal_result',
            )
        finally:
            logger.try_unbind('course', 'assignment')
