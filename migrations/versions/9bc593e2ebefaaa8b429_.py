"""""Creating "can_edit_groups_after_submission" permission.

Revision ID: 9bc593e2ebefaaa8b429
Revises: f7a85c0ba5b06b7dd2b3
Create Date: 2018-11-18 21:07:51.497214

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '9bc593e2ebefaaa8b429'
down_revision = 'f7a85c0ba5b06b7dd2b3'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(text("""
    INSERT INTO "Permission" (name, default_value, course_permission)
    SELECT 'can_edit_groups_after_submission', False, True WHERE NOT EXISTS
        (SELECT 1 FROM "Permission" WHERE name = 'can_edit_groups_after_submission')
    """))


def downgrade():
    pass
