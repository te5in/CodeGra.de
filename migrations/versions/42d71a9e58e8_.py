"""Merging two migrations

Revision ID: 42d71a9e58e8
Revises: 77d138b081a4, 35ca323c91a5
Create Date: 2018-09-30 22:15:05.852689

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '42d71a9e58e8'
down_revision = ('77d138b081a4', '35ca323c91a5')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
