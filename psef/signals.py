import typing as t
import dataclasses

from typing_extensions import Final

from cg_signals import Dispatcher

if t.TYPE_CHECKING and not getattr(t, 'SPHINX', False):  # pragma: no cover
    # pylint: disable=unused-import
    from . import models
    from . import PsefFlask


def init_app(app: object) -> None:
    pass


@dataclasses.dataclass(frozen=True)
class WorkDeletedData:
    __slots__ = ('deleted_work', 'was_latest', 'new_latest')

    deleted_work: 'models.Work'
    was_latest: bool
    new_latest: t.Optional['models.Work']

    def __post_init__(self) -> None:
        if not self.was_latest:
            assert self.new_latest is None
        if self.new_latest is not None:
            assert self.new_latest.user_id == self.deleted_work.user_id
            assert self.new_latest.assignment_id == self.assignment_id

    @property
    def assignment_id(self) -> int:
        return self.deleted_work.assignment_id

    @property
    def user_id(self) -> int:
        return self.deleted_work.user_id


@dataclasses.dataclass(frozen=True)
class UserToCourseData:
    __slots__ = ('user', 'course')

    user: 'models.User'
    course_role: 'models.CourseRole'


WORK_CREATED = Dispatcher['models.Work']('WORK_CREATED')
GRADE_UPDATED = Dispatcher['models.Work']('GRADE_UPDATED')
ASSIGNMENT_STATE_CHANGED = Dispatcher['models.Assignment'](
    'ASSIGNMENT_STATE_CHANGED'
)
FINALIZE_APP = Dispatcher['PsefFlask']('FINALIZE_APP')
WORK_DELETED = Dispatcher[WorkDeletedData]('WORK_DELETED')
USER_ADDED_TO_COURSE = Dispatcher['UserToCourseData']('USER_ADDED_TO_COURSE')
ASSIGNMENT_CREATED = Dispatcher['models.Assignment']('ASSIGNMENT_CREATED')
