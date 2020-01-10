"""""Creating "can_see_linter_feedback_before_done" permission.

Revision ID: 2c2d83782d1089a743d7
Revises: 7ffeba8afa1912d7ade1
Create Date: 2019-12-24 10:31:00.089626

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '2c2d83782d1089a743d7'
down_revision = '7ffeba8afa1912d7ade1'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(text("""
    INSERT INTO "Permission" (name, default_value, course_permission)
    SELECT 'can_see_linter_feedback_before_done', False, True WHERE NOT EXISTS
        (SELECT 1 FROM "Permission" WHERE name = 'can_see_linter_feedback_before_done')
    """))

    grade_perm_id = conn.execute(text("""
    SELECT id FROM "Permission" WHERE name = 'can_see_grade_before_open' LIMIT 1
    """)).scalar()

    # The "Permission" table is not filled yet when a fresh db instance is
    # created. In that case we don't have to search for roles with the old
    # 'can_see_grade_before_open' permission, because they don't exist yet, and
    # the correct defaults are used anyway.
    if grade_perm_id is None:
        return

    feedback_perm_id = conn.execute(text("""
    SELECT id FROM "Permission" WHERE name = 'can_see_linter_feedback_before_done' LIMIT 1
    """)).scalar()

    roles_with_grade_perm = conn.execute(text("""
    SELECT course_role_id FROM "course_roles-permissions" WHERE permission_id = {}
    """.format(grade_perm_id))).fetchall()

    for role_id, in roles_with_grade_perm:
        conn.execute(text("""
        INSERT INTO "course_roles-permissions" (permission_id, course_role_id)
        VALUES ({}, {})
        """.format(feedback_perm_id, role_id)))


def downgrade():
    pass
