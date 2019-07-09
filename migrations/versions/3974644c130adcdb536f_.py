"""""Creating "can_view_autotest_before_done" permission.

Revision ID: 3974644c130adcdb536f
Revises: 438a67d0aebb3d939246
Create Date: 2019-05-30 12:21:10.053104

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '3974644c130adcdb536f'
down_revision = '438a67d0aebb3d939246'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(text("""
    INSERT INTO "Permission" (name, default_value, course_permission)
    SELECT 'can_view_autotest_before_done', False, True WHERE NOT EXISTS
        (SELECT 1 FROM "Permission" WHERE name = 'can_view_autotest_before_done')
    """))


def downgrade():
    pass
