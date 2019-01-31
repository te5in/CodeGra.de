"""""Creating "can_edit_others_groups" permission.

Revision ID: f7a85c0ba5b06b7dd2b3
Revises: 5f5a521578312bba9a47
Create Date: 2018-11-18 21:00:57.401998

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = 'f7a85c0ba5b06b7dd2b3'
down_revision = '5f5a521578312bba9a47'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(text("""
    INSERT INTO "Permission" (name, default_value, course_permission)
    SELECT 'can_edit_others_groups', False, True WHERE NOT EXISTS
        (SELECT 1 FROM "Permission" WHERE name = 'can_edit_others_groups')
    """))


def downgrade():
    pass
