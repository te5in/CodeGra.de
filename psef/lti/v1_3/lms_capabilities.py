import typing as t
import dataclasses

from typing_extensions import Literal, Protocol

from ...registry import lti_1_3_lms_capabilities


class LMSCapabilities(Protocol):
    @property
    def lms(self) -> str:
        """The name of the LMS."""
        ...


    @property
    def set_deadline(self) -> bool:
        """Is it possible for users to set the deadline of a CodeGrade within
            CodeGrade assignment?

        This should be ``True`` if the LMS does **not** pass the deadline in
        the LTI launch, and ``False`` otherwise.
        """
        ...

    @property
    def set_state(self) -> bool:
        """Should the state of the assignment be set within CodeGrade and not be
            copied from the LMS?

        If ``False`` users are not allowed to change to state of the assignment
        within CodeGrade (they can always set the state to done).
        """
        ...

    @property
    def test_student_name(self) -> t.Optional[str]:
        """If there is a test student in the lms this its full name.
        """
        ...

    @property
    def cookie_post_message(self) -> t.Optional[str]:
        ...


@dataclasses.dataclass(frozen=True)
class _LMSCapabilities:
    lms: str

    set_deadline: bool

    set_state: bool

    test_student_name: t.Optional[str]

    cookie_post_message: t.Optional[str]

    def __post_init__(self) -> None:
        lti_1_3_lms_capabilities.register(self.lms)(self)

    def __to_json__(self) -> t.Mapping[str, t.Union[str, bool]]:
        return dataclasses.asdict(self)


_LMSCapabilities(
    lms='Canvas',
    set_deadline=False,
    set_state=False,
    test_student_name='Test Student',
    cookie_post_message='requestFullWindowLaunch'
)

_LMSCapabilities(
    lms='Blackboard',
    set_deadline=True,
    set_state=True,
    test_student_name=None,
    cookie_post_message=None,
)

_LMSCapabilities(
    lms='Moodle',
    set_deadline=True,
    set_state=True,
    test_student_name=None,
    cookie_post_message=None,
)

lti_1_3_lms_capabilities.freeze()
