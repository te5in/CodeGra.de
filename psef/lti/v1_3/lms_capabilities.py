import typing as t
import dataclasses

from ...registry import lti_1_3_lms_capabilities


@dataclasses.dataclass(frozen=True)
class LMSCapabilities:
    lms: str
    deeplink: bool
    set_deadline: bool
    set_state: bool

    def __post_init__(self) -> None:
        lti_1_3_lms_capabilities.register(self.lms)(self)

    def __to_json__(self) -> t.Mapping[str, t.Union[str, bool]]:
        return dataclasses.asdict(self)


LMSCapabilities(
    lms='Canvas',
    deeplink=False,
    set_deadline=False,
    set_state=False,
)

LMSCapabilities(
    lms='Blackboard',
    deeplink=False,
    set_deadline=True,
    set_state=True,
)

LMSCapabilities(
    lms='Moodle',
    deeplink=False,
    set_deadline=True,
    set_state=True,
)

lti_1_3_lms_capabilities.freeze()
