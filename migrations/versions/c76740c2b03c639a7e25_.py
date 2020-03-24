"""""Creating "can_view_feedback_author" permission.

Revision ID: c76740c2b03c639a7e25
Revises: 456153dac64967b564c5
Create Date: 2020-03-24 14:36:34.982985

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = 'c76740c2b03c639a7e25'
down_revision = '456153dac64967b564c5'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(text("""
    INSERT INTO "Permission" (name, default_value, course_permission)
    SELECT 'can_view_feedback_author', True, True WHERE NOT EXISTS
        (SELECT 1 FROM "Permission" WHERE name = 'can_view_feedback_author')
    """))
    [base_id], = conn.execute("SELECT id from \"Permission\" WHERE name = 'can_see_assignee'").fetchall()
    [perm_id], = conn.execute("SELECT id FROM \"Permission\" WHERE name = 'can_view_feedback_author'").fetchall()
    print(base_id, perm_id)
    conn.execute(text("""
INSERT INTO "course_roles-permissions" (permission_id,
                                        course_role_id)
  (SELECT :perm_id,
          id
   from "Course_Role"
   where id not in
       (select course_role_id
        from "course_roles-permissions"
        where permission_id = :base_id))
    """), perm_id=perm_id, base_id=base_id)


def downgrade():
    pass
