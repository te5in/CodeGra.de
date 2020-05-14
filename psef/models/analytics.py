"""This module defines all models needed for the analytics workspaces

SPDX-License-Identifier: AGPL-3.0-only
"""
import abc
import typing as t

import sqlalchemy
from mypy_extensions import TypedDict
from sqlalchemy.dialects.postgresql import aggregate_order_by

from cg_sqlalchemy_helpers.mixins import IdMixin, TimestampMixin

from . import Base, MyQuery, DbColumn, db
from . import file as file_models
from . import user as user_models
from . import work as work_models
from . import rubric as rubric_models
from . import assignment as assignment_models
from .comment import CommentBase, CommentReply
from ..registry import analytics_data_sources

Y = t.TypeVar('Y')
Z = t.TypeVar('Z')


def _array_agg_and_order(
    to_select: DbColumn[Y],
    order_by: DbColumn[Z],
    *,
    remove_nulls: bool = False
) -> DbColumn[t.Sequence[Y]]:
    res = sqlalchemy.func.array_agg(
        aggregate_order_by(to_select, order_by).asc()
    )
    if remove_nulls:
        res = sqlalchemy.func.array_remove(res, sqlalchemy.sql.null())
    return res


class _SubmissionData(TypedDict, total=True):
    id: int
    created_at: str
    grade: t.Optional[float]
    assignee_id: t.Optional[int]


class AnalyticsWorkspace(IdMixin, TimestampMixin, Base):
    """The class that represents an analytics workspace.

    At the moment this class doesn't contain any state, however that will
    probably change in the future.
    """

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
        """A method to get a query that selects of the submissions in this
            workspace.

        :returns: A query that contains al submissions in this workspace.
        """
        return db.session.query(work_models.Work).filter(
            ~db.session.query(user_models.User).filter(
                user_models.User.is_test_student,
                user_models.User.id == work_models.Work.user_id,
            ).exists(),
            work_models.Work.assignment == self.assignment,
        )

    @property
    def submissions_per_student(self
                                ) -> t.Mapping[int, t.List[_SubmissionData]]:
        """Get the submission data for users within this analytics workspace.

        :returns: A mapping between user id and a list of their
            submissions. Each submission is a dictionary with 4 keys: id (the
            id the submission), created_at (created at of the submission),
            grade (the grade of the submission), and assignee_id (the id of the
            assignee of this submission).
        """
        grades_per_sub = dict(
            work_models.Work.get_rubric_grade_per_work(self.assignment)
        )
        grades_per_sub.update(
            work_models.Work.get_non_rubric_grade_per_work(
                self.assignment,
            )
        )

        query = self.work_query.with_entities(
            work_models.Work.user_id,
            _array_agg_and_order(
                work_models.Work.id,
                work_models.Work.created_at,
            ),
            _array_agg_and_order(
                work_models.Work.created_at,
                work_models.Work.created_at,
            ),
            _array_agg_and_order(
                work_models.Work.assigned_to,
                work_models.Work.created_at,
            )
        ).group_by(
            work_models.Work.user_id,
        )

        return {
            user_id: [
                {
                    'id': sub_id,
                    'created_at': created_at.isoformat(),
                    'grade': grades_per_sub.get(sub_id),
                    'assignee_id': assignee_id,
                } for sub_id, created_at, assignee_id in zip(
                    sub_ids,
                    created_ats,
                    assignee_ids,
                )
            ]
            for user_id, sub_ids, created_ats, assignee_ids in query
        }

    def __to_json__(self) -> t.Mapping[str, object]:
        data_sources = [
            source for (source, cls) in analytics_data_sources.get_all()
            if cls(self).should_include()
        ]

        return {
            'id': self.id,
            'assignment_id': self.assignment_id,
            'student_submissions': self.submissions_per_student,
            'data_sources': data_sources,
        }


T = t.TypeVar('T')


class BaseDataSource(t.Generic[T]):
    """The base class for all data sources.

    Each subclass should implement the ``get_data``.
    """
    __slots__ = ('workspace', )

    def __init__(self, workspace: AnalyticsWorkspace) -> None:
        self.workspace = workspace

    @abc.abstractmethod
    def get_data(self) -> t.Mapping[int, T]:
        """Get the data, the key in this mapping should be the submission id
            the data belongs to.

        :returns: A mapping between a submission id and the data this data
            source provides.
        """
        raise NotImplementedError

    def __to_json__(self) -> t.Mapping[str, t.Union[str, t.Mapping[int, T]]]:
        return {
            'name': analytics_data_sources.find(type(self), ''),
            'data': self.get_data(),
        }

    def should_include(self) -> bool:  # pylint: disable=no-self-use
        """should this data source be included in the associated workspace.
        """
        return True


class _RubricDataSourceModel(TypedDict, total=True):
    item_id: int
    multiplier: float


@analytics_data_sources.register('rubric_data')
class _RubricDataSource(BaseDataSource[t.List[_RubricDataSourceModel]]):
    def get_data(self) -> t.Mapping[int, t.List[_RubricDataSourceModel]]:
        query = self.workspace.work_query.join(
            rubric_models.WorkRubricItem, isouter=True
        ).with_entities(
            work_models.Work.id,
            _array_agg_and_order(
                rubric_models.WorkRubricItem.rubricitem_id,
                rubric_models.WorkRubricItem.rubricitem_id,
                remove_nulls=True,
            ),
            _array_agg_and_order(
                rubric_models.WorkRubricItem.multiplier,
                rubric_models.WorkRubricItem.rubricitem_id,
                remove_nulls=True,
            ),
        ).group_by(work_models.Work.id)

        return {
            work_id: [
                {
                    'item_id': item_id,
                    'multiplier': mult,
                } for item_id, mult in zip(item_ids, mults)
            ]
            for work_id, item_ids, mults in query
        }

    def should_include(self) -> bool:
        return self.workspace.assignment.max_rubric_points is not None


class _InlineFeedbackModel(TypedDict, total=True):
    total_amount: int


@analytics_data_sources.register('inline_feedback')
class _InlineFeedbackDataSource(BaseDataSource[_InlineFeedbackModel]):
    def get_data(self) -> t.Mapping[int, _InlineFeedbackModel]:
        base_with_replies = db.session.query(CommentReply.id).filter(
            CommentReply.comment_base_id == CommentBase.id,
            ~CommentReply.deleted,
        ).exists()
        replies_amount = sqlalchemy.func.count(
            sqlalchemy.sql.case([
                (base_with_replies, 1),
            ])
        )

        # We want outer joins here as we want to also get the count of
        # submissions without files or without comments.
        query = self.workspace.work_query.join(
            file_models.File, isouter=True
        ).join(
            CommentBase, isouter=True
        ).with_entities(
            work_models.Work.id,
            replies_amount,
        ).group_by(work_models.Work.id)

        return {
            work_id: {
                'total_amount': total_amount
            }
            for work_id, total_amount in query
        }
