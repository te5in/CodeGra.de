"""""Creating "can_edit_autotest" permission.

Revision ID: 87c90d15ed70406f4e90
Revises: 2a0f513b526fb7c5adc5
Create Date: 2019-05-30 10:06:03.454964

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '87c90d15ed70406f4e90'
down_revision = '2a0f513b526fb7c5adc5'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(text("""
    INSERT INTO "Permission" (name, default_value, course_permission)
    SELECT 'can_edit_autotest', False, True WHERE NOT EXISTS
        (SELECT 1 FROM "Permission" WHERE name = 'can_edit_autotest')
    """))


def downgrade():
    pass
