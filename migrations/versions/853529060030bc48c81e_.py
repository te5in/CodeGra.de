"""""Creating "can_edit_others_comments" permission.

Revision ID: 853529060030bc48c81e
Revises: 962803fed62c
Create Date: 2020-03-21 22:08:39.922335

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '853529060030bc48c81e'
down_revision = '962803fed62c'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(
        text(
            """
    INSERT INTO "Permission" (name, default_value, course_permission)
    SELECT 'can_edit_others_comments', False, True WHERE NOT EXISTS
        (SELECT 1 FROM "Permission" WHERE name = 'can_edit_others_comments')
    """
        )
    )
    new_perm_id, = conn.execute(
        """SELECT id FROM "Permission" WHERE name = 'can_edit_others_comments'"""
    ).first()

    conn.execute(
        text(
            """
    INSERT INTO "course_roles-permissions" (permission_id, course_role_id) (SELECT
        :new_perm_id, course_role_id from "course_roles-permissions" where permission_id = (SELECT id FROM "Permission" WHERE name = 'can_grade_work')
    )
    """
        ),
        new_perm_id=new_perm_id,
    )


def downgrade():
    pass
