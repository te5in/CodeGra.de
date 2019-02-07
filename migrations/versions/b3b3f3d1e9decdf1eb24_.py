"""""Creating "can_view_others_groups" permission.

Revision ID: b3b3f3d1e9decdf1eb24
Revises: 9bc593e2ebefaaa8b429
Create Date: 2018-11-18 22:03:29.504712

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = 'b3b3f3d1e9decdf1eb24'
down_revision = '9bc593e2ebefaaa8b429'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(text("""
    INSERT INTO "Permission" (name, default_value, course_permission)
    SELECT 'can_view_others_groups', True, True WHERE NOT EXISTS
        (SELECT 1 FROM "Permission" WHERE name = 'can_view_others_groups')
    """))


def downgrade():
    pass
