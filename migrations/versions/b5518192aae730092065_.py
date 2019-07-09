"""""Creating "can_view_autotest_fixture" permission.

Revision ID: b5518192aae730092065
Revises: d21179d613b3f933c895
Create Date: 2019-05-30 16:25:22.810553

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = 'b5518192aae730092065'
down_revision = 'd21179d613b3f933c895'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(text("""
    INSERT INTO "Permission" (name, default_value, course_permission)
    SELECT 'can_view_autotest_fixture', True, True WHERE NOT EXISTS
        (SELECT 1 FROM "Permission" WHERE name = 'can_view_autotest_fixture')
    """))


def downgrade():
    pass
