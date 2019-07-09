"""""Creating "can_view_hidden_autotest_steps" permission.

Revision ID: 438a67d0aebb3d939246
Revises: 87c90d15ed70406f4e90
Create Date: 2019-05-30 10:11:50.573254

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '438a67d0aebb3d939246'
down_revision = '87c90d15ed70406f4e90'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(text("""
    INSERT INTO "Permission" (name, default_value, course_permission)
    SELECT 'can_view_hidden_autotest_steps', False, True WHERE NOT EXISTS
        (SELECT 1 FROM "Permission" WHERE name = 'can_view_hidden_autotest_steps')
    """))


def downgrade():
    pass
