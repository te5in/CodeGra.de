"""""Creating "can_edit_own_groups" permission.

Revision ID: 5f5a521578312bba9a47
Revises: 6125751db2df
Create Date: 2018-11-18 20:57:54.899887

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '5f5a521578312bba9a47'
down_revision = '6125751db2df'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(text("""
    INSERT INTO "Permission" (name, default_value, course_permission)
    SELECT 'can_edit_own_groups', True, True WHERE NOT EXISTS
        (SELECT 1 FROM "Permission" WHERE name = 'can_edit_own_groups')
    """))


def downgrade():
    pass
