"""""Creating "can_delete_autotest_run" permission.

Revision ID: 2a0f513b526fb7c5adc5
Revises: a5ebacac357ca471487d
Create Date: 2019-05-30 10:04:39.623596

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '2a0f513b526fb7c5adc5'
down_revision = 'a5ebacac357ca471487d'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(text("""
    INSERT INTO "Permission" (name, default_value, course_permission)
    SELECT 'can_delete_autotest_run', False, True WHERE NOT EXISTS
        (SELECT 1 FROM "Permission" WHERE name = 'can_delete_autotest_run')
    """))


def downgrade():
    pass
