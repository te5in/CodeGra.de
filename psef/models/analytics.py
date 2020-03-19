import abc
import typing as t

import sqlalchemy
from sqlalchemy.dialects.postgresql import aggregate_order_by

from cg_sqlalchemy_helpers.mixins import IdMixin, TimestampMixin

from . import Base, db
from . import work as work_models
from . import assignment as assignment_models
from ..registry import analytics_data_sources

T = t.TypeVar('T')


class AnalyticsWorkspace(IdMixin, TimestampMixin, Base):
    assignment_id = db.Column(
        'assignment_id',
        db.Integer,
        db.ForeignKey('Assignment.id', ondelete='CASCADE'),
        nullable=False,
    )
    assignment = db.relationship(
        lambda: assignment_models.Assignment,
        foreign_keys=assignment_id,
        back_populates='analytics_workspaces',
    )

    @property
    def submission_ids_per_student(self) -> t.Mapping[int, t.List[int]]:
        return dict(
            db.session.query(
                work_models.Work.user_id,
                sqlalchemy.func.array_agg(
                    aggregate_order_by(
                        work_models.Work.id, work_models.Work.created_at
                    ).asc()
                )
            ).filter(
                work_models.Work.assignment == self.assignment,
            ).group_by(
                work_models.Work.user_id,
            )
        )

    def __to_json__(self) -> t.Mapping[str, object]:
        return {
            'id': self.id,
            'assignment_id': self.assignment_id,
            'student_submission_ids': self.submission_ids_per_student,
            'data_sources': list(analytics_data_sources.keys())
        }


class BaseDataSource(t.Generic[T]):
    def __init__(self, workspace: AnalyticsWorkspace) -> None:
        self.workspace = workspace

    @abc.abstractmethod
    def get_data(self) -> t.Mapping[int, T]:
        raise NotImplementedError

    def __to_json__(self) -> t.Mapping[str, t.Union[str, t.Mapping[int, T]]]:
        return {
            'name': analytics_data_sources.find(type(self)),
            'data': self.get_data(),
        }
