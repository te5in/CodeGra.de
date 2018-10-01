"""Merge two migrations

Revision ID: 35ca323c91a5
Revises: 19f00a8b1316, 8693e277a9ac
Create Date: 2018-09-27 13:22:48.216750

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '35ca323c91a5'
down_revision = ('19f00a8b1316', '8693e277a9ac')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
