"""""Creating "can_edit_group_set" permission.

Revision ID: c956e2d2c0d3e697102b
Revises: 450189fa482b
Create Date: 2019-01-29 22:41:41.016800

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = 'c956e2d2c0d3e697102b'
down_revision = '450189fa482b'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(text("""
    INSERT INTO "Permission" (name, default_value, course_permission)
    SELECT 'can_edit_group_set', False, True WHERE NOT EXISTS
        (SELECT 1 FROM "Permission" WHERE name = 'can_edit_group_set')
    """))


def downgrade():
    pass
