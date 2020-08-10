"""Makes sure assignment only has one peer feedback setting

Revision ID: bd7be2a11e1c
Revises: e5e51a288e22270b1ae5
Create Date: 2020-07-13 12:25:09.617411

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import sqlalchemy_utils

# revision identifiers, used by Alembic.
revision = 'bd7be2a11e1c'
down_revision = 'e5e51a288e22270b1ae5'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint('unique_assignment_peer_feeback_settings', 'assignment_peer_feedback_settings', ['assignment_id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('unique_assignment_peer_feeback_settings', 'assignment_peer_feedback_settings', type_='unique')
    # ### end Alembic commands ###