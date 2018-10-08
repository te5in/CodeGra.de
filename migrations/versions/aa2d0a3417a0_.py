"""Add virtual columns to user and course

Revision ID: aa2d0a3417a0
Revises: 19f00a8b1316
Create Date: 2018-09-16 12:36:05.118121

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'aa2d0a3417a0'
down_revision = '19f00a8b1316'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('Course', sa.Column('virtual', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('User', sa.Column('virtual', sa.Boolean(), nullable=False, server_default='false'))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('User', 'virtual')
    op.drop_column('Course', 'virtual')
    # ### end Alembic commands ###
