"""Add logo and description columns

Revision ID: 865724dddab2
Revises: e8fd2984d6b9
Create Date: 2020-08-04 17:43:49.423399

"""
import sqlalchemy as sa
import sqlalchemy_utils
from alembic import op

# revision identifiers, used by Alembic.
revision = '865724dddab2'
down_revision = 'e8fd2984d6b9'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        'saml2_provider', sa.Column('logo', sa.LargeBinary(), nullable=False)
    )
    op.add_column(
        'saml2_provider',
        sa.Column('description', sa.Unicode(), nullable=False)
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('saml2_provider', 'logo')
    op.drop_column('saml2_provider', 'description')
    # ### end Alembic commands ###