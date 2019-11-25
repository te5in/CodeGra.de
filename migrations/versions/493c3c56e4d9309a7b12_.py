"""""Creating "can_view_autotest_output_files_before_done" permission.

Revision ID: 493c3c56e4d9309a7b12
Revises: 0ed7db5d0b70
Create Date: 2019-11-14 09:56:57.706049

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '493c3c56e4d9309a7b12'
down_revision = '0ed7db5d0b70'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(text("""
    INSERT INTO "Permission" (name, default_value, course_permission)
    SELECT 'can_view_autotest_output_files_before_done', False, True WHERE NOT EXISTS
        (SELECT 1 FROM "Permission" WHERE name = 'can_view_autotest_output_files_before_done')
    """))


def downgrade():
    pass
