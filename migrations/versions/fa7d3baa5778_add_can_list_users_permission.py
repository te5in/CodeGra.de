"""Add can_list_users permission

Revision ID: fa7d3baa5778
Revises: 42d71a9e58e8
Create Date: 2018-10-02 18:50:41.298783

SPDX-License-Identifier: AGPL-3.0-only
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

revision = 'fa7d3baa5778'
down_revision = '42d71a9e58e8'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(
        text(
            """
    INSERT INTO "Permission" (name, default_value, course_permission)
    SELECT 'can_list_course_users', true, true WHERE NOT EXISTS
        (SELECT 1 FROM "Permission" WHERE name = 'can_list_course_users')
    """
        )
    )


def downgrade():
    pass
