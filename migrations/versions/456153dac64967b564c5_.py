"""""Creating "can_view_others_comment_edits" permission.

Revision ID: 456153dac64967b564c5
Revises: 07eb464c56886d188ca8
Create Date: 2020-03-24 11:34:07.710267

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '456153dac64967b564c5'
down_revision = '07eb464c56886d188ca8'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(text("""
    INSERT INTO "Permission" (name, default_value, course_permission)
    SELECT 'can_view_others_comment_edits', False, True WHERE NOT EXISTS
        (SELECT 1 FROM "Permission" WHERE name = 'can_view_others_comment_edits')
    """))


def downgrade():
    pass
