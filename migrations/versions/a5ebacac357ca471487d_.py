"""""Creating "can_run_autotest" permission.

Revision ID: a5ebacac357ca471487d
Revises: 7f18e98b7043
Create Date: 2019-05-30 10:03:12.981879

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = 'a5ebacac357ca471487d'
down_revision = '7f18e98b7043'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(text("""
    INSERT INTO "Permission" (name, default_value, course_permission)
    SELECT 'can_run_autotest', False, True WHERE NOT EXISTS
        (SELECT 1 FROM "Permission" WHERE name = 'can_run_autotest')
    """))


def downgrade():
    pass
