"""""Creating "can_impersonate_users" permission.

Revision ID: 76c1a7c2f156f7a2d5aa
Revises: 9c83395350ac
Create Date: 2019-10-15 08:24:03.188886

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '76c1a7c2f156f7a2d5aa'
down_revision = '9c83395350ac'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(text("""
    INSERT INTO "Permission" (name, default_value, course_permission)
    SELECT 'can_impersonate_users', False, False WHERE NOT EXISTS
        (SELECT 1 FROM "Permission" WHERE name = 'can_impersonate_users')
    """))


def downgrade():
    pass
