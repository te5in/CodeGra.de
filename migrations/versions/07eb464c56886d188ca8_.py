"""""Creating "can_add_own_inline_comments" permission.

Revision ID: 07eb464c56886d188ca8
Revises: 05fe57e91882
Create Date: 2020-03-24 11:18:45.465395

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '07eb464c56886d188ca8'
down_revision = '05fe57e91882'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(text("""
    INSERT INTO "Permission" (name, default_value, course_permission)
    SELECT 'can_add_own_inline_comments', false, True WHERE NOT EXISTS
        (SELECT 1 FROM "Permission" WHERE name = 'can_add_own_inline_comments')
    """))


def downgrade():
    pass
