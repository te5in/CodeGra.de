"""Add grade calculation column

Revision ID: 3dc6f1de1017
Revises: f9a29920788a
Create Date: 2019-06-26 18:43:58.583274

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils

# revision identifiers, used by Alembic.
revision = '3dc6f1de1017'
down_revision = 'f9a29920788a'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    context = op.get_context()
    if context.bind.dialect.name == 'postgresql':
        bind = op.get_bind()
        has_size_type = bind.execute(
                "select exists (select 1 from pg_type "
                "where typname='grade_calculation_enum')").scalar()
        if not has_size_type:
            op.execute("CREATE TYPE grade_calculation_enum AS ENUM ('full', 'partial')")
    op.add_column('AutoTest', sa.Column('grade_calculation', sa.Enum('full', 'partial', name='grade_calculation_enum', create=True), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('AutoTest', 'grade_calculation')
    # ### end Alembic commands ###