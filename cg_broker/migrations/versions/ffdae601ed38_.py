"""Add settings table

Revision ID: ffdae601ed38
Revises: d5a088f2feaa
Create Date: 2020-01-28 14:42:45.074347

"""
import sqlalchemy as sa
import sqlalchemy_utils
from alembic import op

# revision identifiers, used by Alembic.
revision = 'ffdae601ed38'
down_revision = 'd5a088f2feaa'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        'setting', sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column(
            'settting',
            sa.Enum('minimum_amount_extra_runners', name='possiblesetting'),
            nullable=False
        ), sa.Column('value', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('settting')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('setting')
    # ### end Alembic commands ###
