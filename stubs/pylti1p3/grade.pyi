import typing as t

from typing_extensions import Literal

T_SELF = t.TypeVar('T_SELF', bound='Grade')


class Grade:
    def set_score_given(self: T_SELF, value: float) -> T_SELF:
        ...

    def set_score_maximum(self: T_SELF, value: float) -> T_SELF:
        ...

    def set_activity_progress(
        self: T_SELF,
        value: Literal['Initialized', 'Started', 'InProgress', 'Submitted',
                       'Completed'],
    ) -> T_SELF:
        ...

    def set_grading_progress(
        self: T_SELF,
        value: Literal['FullyGraded', 'Pending', 'PendingManual', 'Failed',
                       'NotReady'],
    ) -> T_SELF:
        ...

    def set_timestamp(self: T_SELF, value: str) -> T_SELF:
        ...

    def set_user_id(self: T_SELF, value: str) -> T_SELF:
        ...
