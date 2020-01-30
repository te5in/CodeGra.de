"""""Creating "can_override_submission_limiting" permission.

Revision ID: 0a6c16ad4847de44317e
Revises: 7ffeba8afa1912d7ade1
Create Date: 2020-01-06 12:27:18.687206

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '0a6c16ad4847de44317e'
down_revision = '7ffeba8afa1912d7ade1'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(text("""
    INSERT INTO "Permission" (name, default_value, course_permission)
    SELECT 'can_override_submission_limiting', False, True WHERE NOT EXISTS
        (SELECT 1 FROM "Permission" WHERE name = 'can_override_submission_limiting')
    """))


def downgrade():
    pass
