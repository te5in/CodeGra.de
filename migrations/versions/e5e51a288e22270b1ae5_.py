"""""Creating "can_edit_peer_feedback_settings" permission.

Revision ID: e5e51a288e22270b1ae5
Revises: 845c0ab60c02
Create Date: 2020-07-13 09:04:49.572755

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = 'e5e51a288e22270b1ae5'
down_revision = '845c0ab60c02'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    exists = conn.execute(text("""SELECT id from "Permission" where name = :perm_name"""), perm_name='can_edit_peer_feedback_settings').fetchall()
    if exists:
        return

    new_perm_id = conn.execute(text("""
    INSERT INTO "Permission" (name, default_value, course_permission)
    SELECT :perm_name, :default_value, :course_permission RETURNING id
    """), perm_name='can_edit_peer_feedback_settings', default_value=False, course_permission=True).scalar()

    old_perm_id = conn.execute(text("""
    SELECT id FROM "Permission" WHERE name = :perm_name LIMIT 1
    """), perm_name='can_edit_assignment_info').scalar()
    
    conn.execute(text("""
    INSERT INTO "course_roles-permissions" (permission_id, course_role_id)
            SELECT :new_perm_id, course_role_id FROM "course_roles-permissions"
                WHERE permission_id = :old_perm_id
    """), old_perm_id=old_perm_id, new_perm_id=new_perm_id)

def downgrade():
    pass
