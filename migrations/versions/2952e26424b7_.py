"""Merge migrations

Revision ID: 2952e26424b7
Revises: bec486c454ff, 42d71a9e58e8
Create Date: 2018-10-03 17:28:03.670105

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2952e26424b7'
down_revision = ('bec486c454ff', '42d71a9e58e8')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
