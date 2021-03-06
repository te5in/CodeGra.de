"""Add saml2 provider to user connection table

Revision ID: b987d88cc27d
Revises: 8bf73796b4d7
Create Date: 2020-08-03 10:56:40.357729

"""
import sqlalchemy as sa
import sqlalchemy_utils
from alembic import op

# revision identifiers, used by Alembic.
revision = 'b987d88cc27d'
down_revision = '8bf73796b4d7'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        'user_saml_provider',
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column(
            'saml2_provider_id',
            sqlalchemy_utils.types.uuid.UUIDType(),
            nullable=False
        ),
        sa.Column('name_id', sa.Unicode(), nullable=False),
        sa.ForeignKeyConstraint(['saml2_provider_id'], ['saml2_provider.id']),
        sa.ForeignKeyConstraint(['user_id'], ['User.id']),
        sa.PrimaryKeyConstraint('user_id', 'saml2_provider_id'),
        sa.UniqueConstraint('saml2_provider_id', 'name_id'),
    )
    op.create_index(
        op.f('ix_user_saml_provider_name_id'),
        'user_saml_provider',
        ['name_id'],
        unique=False,
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(
        op.f('ix_user_saml_provider_name_id'), table_name='user_saml_provider'
    )
    op.drop_table('user_saml_provider')
    # ### end Alembic commands ###
