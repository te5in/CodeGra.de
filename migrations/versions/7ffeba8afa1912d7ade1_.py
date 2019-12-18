"""""Creating "can_delete_assignments" permission.

Revision ID: 7ffeba8afa1912d7ade1
Revises: 0ab8d5e2eab2
Create Date: 2019-12-13 10:57:16.882775

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '7ffeba8afa1912d7ade1'
down_revision = '0ab8d5e2eab2'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(text("""
    INSERT INTO "Permission" (name, default_value, course_permission)
    SELECT 'can_delete_assignments', False, True WHERE NOT EXISTS
        (SELECT 1 FROM "Permission" WHERE name = 'can_delete_assignments')
    """))


def downgrade():
    pass
