"""""Creating "can_view_hidden_fixtures" permission.

Revision ID: 46964ce1a243f3453181
Revises: 8011959a297b
Create Date: 2019-05-07 10:07:55.716183

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '46964ce1a243f3453181'
down_revision = '8011959a297b'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(text("""
    INSERT INTO "Permission" (name, default_value, course_permission)
    SELECT 'can_view_hidden_fixtures', False, True WHERE NOT EXISTS
        (SELECT 1 FROM "Permission" WHERE name = 'can_view_hidden_fixtures')
    """))


def downgrade():
    pass
