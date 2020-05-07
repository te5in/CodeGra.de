import typing as t
import dataclasses

from typing_extensions import Protocol

from ...registry import lti_1_3_lms_capabilities


class LMSCapabilities(Protocol):
    @property
    def lms(self) -> str:
        """The name of the LMS."""
        ...

    @property
    def deeplink_allowed(self) -> bool:
        """Should the LMS be allowed to do a deeplink request.

        This should only be `True`` if this actually adds anything to the
        experience for the user.
        """
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


@dataclasses.dataclass(frozen=True)
class _LMSCapabilities:
    lms: str

    deeplink_allowed: bool

    set_deadline: bool

    set_state: bool

    def __post_init__(self) -> None:
        lti_1_3_lms_capabilities.register(self.lms)(self)

    def __to_json__(self) -> t.Mapping[str, t.Union[str, bool]]:
        return dataclasses.asdict(self)


_LMSCapabilities(
    lms='Canvas',
    deeplink_allowed=False,
    set_deadline=False,
    set_state=False,
)

_LMSCapabilities(
    lms='Blackboard',
    deeplink_allowed=False,
    set_deadline=True,
    set_state=True,
)

_LMSCapabilities(
    lms='Moodle',
    deeplink_allowed=False,
    set_deadline=True,
    set_state=True,
)

lti_1_3_lms_capabilities.freeze()
