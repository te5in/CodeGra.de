"""Add the `is_test_student` column

Revision ID: 2b1796c59c7d
Revises: 51a1f625330d
Create Date: 2019-09-02 13:48:57.545353

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils

# revision identifiers, used by Alembic.
revision = '2b1796c59c7d'
down_revision = '51a1f625330d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('User', sa.Column('is_test_student', sa.Boolean(), nullable=False, server_default='false'))
    op.create_index(op.f('ix_User_is_test_student'), 'User', ['is_test_student'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_User_is_test_student'), table_name='User')
    op.drop_column('User', 'is_test_student')
    # ### end Alembic commands ###
