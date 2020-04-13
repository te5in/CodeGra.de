"""""Creating "can_view_analytics" permission.

Revision ID: 81b6a7bffdc9ddf940e7
Revises: da889c40b2a7
Create Date: 2020-04-07 08:57:52.503517

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '81b6a7bffdc9ddf940e7'
down_revision = 'da889c40b2a7'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(text("""
    INSERT INTO "Permission" (name, default_value, course_permission)
    SELECT 'can_view_analytics', False, True WHERE NOT EXISTS
        (SELECT 1 FROM "Permission" WHERE name = 'can_view_analytics')
    """))

    edit_roles_id = conn.execute(text("""
    SELECT id FROM "Permission" WHERE name = 'can_edit_course_roles' LIMIT 1
    """)).scalar()

    # The "Permission" table is not filled yet when a fresh db instance is
    # created. In that case we don't have to search for roles with the old
    # 'can_see_grade_before_open' permission, because they don't exist yet, and
    # the correct defaults are used anyway.
    if edit_roles_id is None:
        return

    view_analytics_id = conn.execute(text("""
    SELECT id FROM "Permission" WHERE name = 'can_view_analytics' LIMIT 1
    """)).scalar()

    roles_with_edit_perm = conn.execute(text("""
    SELECT course_role_id FROM "course_roles-permissions" WHERE permission_id = {}
    """.format(edit_roles_id))).fetchall()

    for role_id, in roles_with_edit_perm:
        conn.execute(text("""
        INSERT INTO "course_roles-permissions" (permission_id, course_role_id)
        VALUES ({}, {})
        """.format(view_analytics_id, role_id)))


def downgrade():
    pass
