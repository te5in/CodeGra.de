"""Merge migrations

Revision ID: 30495211ae0c
Revises: fa7d3baa5778, 2952e26424b7
Create Date: 2018-10-04 02:28:02.761982

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '30495211ae0c'
down_revision = ('fa7d3baa5778', '2952e26424b7')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
