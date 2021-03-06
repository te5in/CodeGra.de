"""Add runners_requested column

Revision ID: 51a1f625330d
Revises: b95df1528b32
Create Date: 2019-08-23 14:49:29.187286

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils

# revision identifiers, used by Alembic.
revision = '51a1f625330d'
down_revision = 'b95df1528b32'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('AutoTestRun', sa.Column('runners_requested', sa.Integer(), server_default='0', nullable=False))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('AutoTestRun', 'runners_requested')
    # ### end Alembic commands ###
