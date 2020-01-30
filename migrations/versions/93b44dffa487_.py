"""Add column needed for continuous rubrics

Revision ID: 93b44dffa487
Revises: 7ffeba8afa1912d7ade1
Create Date: 2019-12-25 15:15:30.305831

"""
import sqlalchemy as sa
import sqlalchemy_utils
from alembic import op

# revision identifiers, used by Alembic.
revision = '93b44dffa487'
down_revision = '7ffeba8afa1912d7ade1'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    context = op.get_context()
    if context.bind.dialect.name == 'postgresql':
        bind = op.get_bind()
        has_rubric_type = bind.execute(
            "select exists (select 1 from pg_type "
            "where typname='rubricrowtype')"
        ).scalar()
        if not has_rubric_type:
            op.execute(
                "CREATE TYPE rubricrowtype AS ENUM ('normal', 'continuous')"
            )

    op.add_column(
        'RubricRow',
        sa.Column(
            'rubric_row_type',
            sa.Enum('continuous', 'normal', name='rubricrowtype'),
            server_default='normal',
            nullable=False
        )
    )
    op.add_column(
        'work_rubric_item',
        sa.Column(
            'multiplier', sa.Float(), server_default='1.0', nullable=False
        )
    )
    op.create_check_constraint(
        'ck_multiplier_range',
        'work_rubric_item',
        'multiplier >= 0 AND multiplier <= 1',
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('work_rubric_item', 'multiplier')
    op.drop_column('RubricRow', 'rubric_row_type')
    op.drop_constraint(
        'ck_multiplier_range',
        'work_rubric_item',
    )
    # ### end Alembic commands ###
