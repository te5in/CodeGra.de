"""Add prefer_teacher_revision column to AutoTest table

Revision ID: 7f5b06f81aef
Revises: effc355fddff
Create Date: 2020-07-01 16:44:05.244310

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import sqlalchemy_utils

# revision identifiers, used by Alembic.
revision = '7f5b06f81aef'
down_revision = 'effc355fddff'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('AutoTest', sa.Column('prefer_teacher_revision', sa.Boolean(), nullable=True))
    conn.execute(text("""
    UPDATE "AutoTest" SET prefer_teacher_revision = false;
    """))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('AutoTest', 'prefer_teacher_revision')
    # ### end Alembic commands ###
