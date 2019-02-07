"""""Creating "can_create_groups" permission.

Revision ID: f2563a55410c7c6d3d38
Revises: c956e2d2c0d3e697102b
Create Date: 2019-02-06 13:18:55.071085

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = 'f2563a55410c7c6d3d38'
down_revision = 'c956e2d2c0d3e697102b'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(text("""
    INSERT INTO "Permission" (name, default_value, course_permission)
    SELECT 'can_create_groups', True, True WHERE NOT EXISTS
        (SELECT 1 FROM "Permission" WHERE name = 'can_create_groups')
    """))


def downgrade():
    pass
