import abc
import typing as t

import sqlalchemy
from mypy_extensions import TypedDict
from sqlalchemy.dialects.postgresql import aggregate_order_by

from cg_sqlalchemy_helpers.mixins import IdMixin, TimestampMixin

from . import Base, MyQuery, DbColumn, db
from . import file as file_models
from . import work as work_models
from . import rubric as rubric_models
from . import assignment as assignment_models
from .comment import Comment
from ..registry import analytics_data_sources

Y = t.TypeVar('Y')
Z = t.TypeVar('Z')


def _array_agg_and_order(to_select: DbColumn[Y],
                         order_by: DbColumn[Z]) -> DbColumn[t.List[Y]]:
    return sqlalchemy.func.array_agg(
        aggregate_order_by(to_select, order_by).asc()
    )


class _SubmissionData(TypedDict, total=True):
    id: int
    created_at: str
    grade: t.Optional[float]


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
    def submissions_per_student(self
                                ) -> t.Mapping[int, t.List[_SubmissionData]]:
        grades_per_sub = dict(
            work_models.Work.get_rubric_grade_per_work(self.assignment)
        )
        grades_per_sub.update(
            db.session.query(
                work_models.Work.id, work_models.Work._grade
            ).filter(
                work_models.Work.assignment == self.assignment,
                work_models.Work._grade.isnot(None),
            )
        )

        query = db.session.query(
            work_models.Work.user_id,
            _array_agg_and_order(
                work_models.Work.id,
                work_models.Work.created_at,
            ),
            _array_agg_and_order(
                work_models.Work.created_at,
                work_models.Work.created_at,
            ),
        ).filter(
            work_models.Work.assignment == self.assignment,
        ).group_by(
            work_models.Work.user_id,
        )

        return {
            user_id: [
                {
                    'id': sub_id,
                    'created_at': created_at.isoformat(),
                    'grade': grades_per_sub.get(sub_id),
                } for sub_id, created_at in zip(sub_ids, created_ats)
            ]
            for user_id, sub_ids, created_ats in query
        }

    def __to_json__(self) -> t.Mapping[str, object]:
        return {
            'id': self.id,
            'assignment_id': self.assignment_id,
            'student_submissions': self.submissions_per_student,
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


class _InlineFeedbackModel(TypedDict, total=True):
    total_amount: int


@analytics_data_sources.register('inline_feedback')
class _InlineFeedbackDataSource(BaseDataSource[_InlineFeedbackModel]):
    def get_data(self) -> t.Mapping[int, _InlineFeedbackModel]:
        # We want outer joins here as we want to also get the count of
        # submissions without files or without comments.
        query = self.workspace.work_query.join(
            file_models.File, isouter=True
        ).join(
            Comment, isouter=True
        ).with_entities(
            work_models.Work.id,
            sqlalchemy.func.count(Comment.file_id),
        ).group_by(work_models.Work.id)

        return dict(query)
