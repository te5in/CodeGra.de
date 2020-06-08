"""""Creating "can_manage_lti_providers" permission.

Revision ID: 97234ea957585a44f5f1
Revises: 73493f66f88d
Create Date: 2020-05-25 09:32:05.467672

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '97234ea957585a44f5f1'
down_revision = '73493f66f88d'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    exists = conn.execute(text("""SELECT id from "Permission" where name = :perm_name"""), perm_name='can_manage_lti_providers').fetchall()
    if exists:
        return

    new_perm_id = conn.execute(text("""
    INSERT INTO "Permission" (name, default_value, course_permission)
    SELECT :perm_name, :default_value, :course_permission RETURNING id
    """), perm_name='can_manage_lti_providers', default_value=False, course_permission=False).scalar()



def downgrade():
    pass
