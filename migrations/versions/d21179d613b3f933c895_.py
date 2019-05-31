"""""Creating "can_view_autotest_step_details" permission.

Revision ID: d21179d613b3f933c895
Revises: 3974644c130adcdb536f
Create Date: 2019-05-30 12:30:07.077174

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = 'd21179d613b3f933c895'
down_revision = '3974644c130adcdb536f'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(text("""
    INSERT INTO "Permission" (name, default_value, course_permission)
    SELECT 'can_view_autotest_step_details', True, True WHERE NOT EXISTS
        (SELECT 1 FROM "Permission" WHERE name = 'can_view_autotest_step_details')
    """))


def downgrade():
    pass
