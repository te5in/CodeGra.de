"""Add updates_lti1p1_id column

Revision ID: 8746cca4f4b4
Revises: 6dd3c8494722
Create Date: 2020-06-15 10:38:23.847637

"""
import sqlalchemy as sa
import sqlalchemy_utils
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '8746cca4f4b4'
down_revision = '6dd3c8494722'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('LTIProvider', sa.Column('updates_lti1p1_id', sa.String(length=36), nullable=True))
    op.create_foreign_key('updates_lti1p1_id_fkey', 'LTIProvider', 'LTIProvider', ['updates_lti1p1_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('updates_lti1p1_id_fkey', 'LTIProvider', type_='foreignkey')
    op.drop_column('LTIProvider', 'updates_lti1p1_id')
    # ### end Alembic commands ###
