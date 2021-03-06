"""Remove useless key_set column

Revision ID: 5d92f0ee825a
Revises: 8b8cf97cd9be
Create Date: 2020-02-19 14:59:41.540189

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils

# revision identifiers, used by Alembic.
revision = '5d92f0ee825a'
down_revision = '8b8cf97cd9be'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('LTIProvider', 'key_set')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('LTIProvider', sa.Column('key_set', sa.VARCHAR(), autoincrement=False, nullable=True))
    # ### end Alembic commands ###
