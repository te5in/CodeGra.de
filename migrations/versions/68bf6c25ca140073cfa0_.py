"""""Creating "can_approve_inline_comments" permission.

Revision ID: 68bf6c25ca140073cfa0
Revises: 4fa55485e7b2ea40ebd4
Create Date: 2020-06-24 12:45:37.164814

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '68bf6c25ca140073cfa0'
down_revision = '4fa55485e7b2ea40ebd4'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    exists = conn.execute(text("""SELECT id from "Permission" where name = :perm_name"""), perm_name='can_approve_inline_comments').fetchall()
    if exists:
        return

    new_perm_id = conn.execute(text("""
    INSERT INTO "Permission" (name, default_value, course_permission)
    SELECT :perm_name, :default_value, :course_permission RETURNING id
    """), perm_name='can_approve_inline_comments', default_value=False, course_permission=True).scalar()

    old_perm_id = conn.execute(text("""
    SELECT id FROM "Permission" WHERE name = :perm_name LIMIT 1
    """), perm_name='can_view_inline_feedback_before_approved').scalar()
    
    conn.execute(text("""
    INSERT INTO "course_roles-permissions" (permission_id, course_role_id)
            SELECT :new_perm_id, course_role_id FROM "course_roles-permissions"
                WHERE permission_id = :old_perm_id
    """), old_perm_id=old_perm_id, new_perm_id=new_perm_id)

def downgrade():
    pass
