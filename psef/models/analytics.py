import abc
import typing as t

import sqlalchemy
from mypy_extensions import TypedDict
from sqlalchemy.dialects.postgresql import aggregate_order_by

from cg_sqlalchemy_helpers.mixins import IdMixin, TimestampMixin

from . import Base, MyQuery, DbColumn, db
from . import work as work_models
from . import rubric as rubric_models
from . import assignment as assignment_models
from ..registry import analytics_data_sources

Y = t.TypeVar('Y')
Z = t.TypeVar('Z')


def _array_agg_and_order(to_select: DbColumn[Y],
                         order_by: DbColumn[Z]) -> DbColumn[t.List[Y]]:
    return sqlalchemy.func.array_agg(
        aggregate_order_by(to_select, order_by).asc()
    )


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
    def work_query(self) -> MyQuery['work_models.Work']:
        return db.session.query(
            work_models.Work
        ).filter(work_models.Work.assignment == self.assignment)

    @property
    def submission_ids_per_student(self) -> t.Mapping[int, t.List[int]]:
        return dict(
            db.session.query(
                work_models.Work.user_id,
                _array_agg_and_order(
                    work_models.Work.id, work_models.Work.created_at
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


T = t.TypeVar('T')


class BaseDataSource(t.Generic[T]):
    def __init__(self, workspace: AnalyticsWorkspace) -> None:
        self.workspace = workspace

    @abc.abstractmethod
    def get_data(self) -> t.Mapping[int, T]:
        """Get the data, the key in this mapping should be the submission id
        the data belongs to.
        """
        raise NotImplementedError

    def __to_json__(self) -> t.Mapping[str, t.Union[str, t.Mapping[int, T]]]:
        return {
            'name': analytics_data_sources.find(type(self), ''),
            'data': self.get_data(),
        }


class _RubricDataSourceModel(TypedDict, total=True):
    item_id: int
    multiplier: float


@analytics_data_sources.register('rubric_data')
class _RubricDataSource(BaseDataSource[t.List[_RubricDataSourceModel]]):
    def get_data(self) -> t.Mapping[int, t.List[_RubricDataSourceModel]]:
        query = db.session.query(
            rubric_models.WorkRubricItem.work_id,
            _array_agg_and_order(
                rubric_models.WorkRubricItem.rubricitem_id,
                rubric_models.WorkRubricItem.rubricitem_id,
            ),
            _array_agg_and_order(
                rubric_models.WorkRubricItem.multiplier,
                rubric_models.WorkRubricItem.rubricitem_id,
            ),
        ).filter(
            rubric_models.WorkRubricItem.work_id.in_(
                self.workspace.work_query.with_entities(work_models.Work.id)
            )
        ).group_by(rubric_models.WorkRubricItem.work_id)
        return {
            work_id: [
                {
                    'item_id': item_id,
                    'multiplier': mult,
                } for item_id, mult in zip(item_ids, mults)
            ]
            for work_id, item_ids, mults in query
        }
