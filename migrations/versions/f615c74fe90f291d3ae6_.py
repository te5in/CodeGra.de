"""""Creating "can_edit_group_assignment" permission.

Revision ID: f615c74fe90f291d3ae6
Revises: b3b3f3d1e9decdf1eb24
Create Date: 2018-11-19 09:41:59.975896

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = 'f615c74fe90f291d3ae6'
down_revision = 'b3b3f3d1e9decdf1eb24'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(text("""
    INSERT INTO "Permission" (name, default_value, course_permission)
    SELECT 'can_edit_group_assignment', False, True WHERE NOT EXISTS
        (SELECT 1 FROM "Permission" WHERE name = 'can_edit_group_assignment')
    """))


def downgrade():
    pass
