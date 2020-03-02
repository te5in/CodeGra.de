"""Add comment_author field

Revision ID: e1f30937ba40
Revises: fa7d3baa5778
Create Date: 2018-10-04 16:19:32.926640

SPDX-License-Identifier: AGPL-3.0-only
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'e1f30937ba40'
down_revision = 'fa7d3baa5778'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('Work', sa.Column('comment_author_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'Work', 'User', ['comment_author_id'], ['id'], ondelete='SET NULL')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'Work', type_='foreignkey')
    op.drop_column('Work', 'comment_author_id')
    # ### end Alembic commands ###