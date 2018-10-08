"""Merge migration

Revision ID: d8252005c937
Revises: e1f30937ba40, 30495211ae0c
Create Date: 2018-10-08 17:46:35.262347

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd8252005c937'
down_revision = ('e1f30937ba40', '30495211ae0c')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
