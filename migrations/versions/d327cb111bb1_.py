"""Add table for indication grader state and add fields for reminders.

Revision ID: d327cb111bb1
Revises: ddb38c4abccc
Create Date: 2017-12-07 17:53:39.720706

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM

# revision identifiers, used by Alembic.
revision = 'd327cb111bb1'
down_revision = 'ddb38c4abccc'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        'AssignmentGraderDone',
        sa.Column('User_id', sa.Integer(), nullable=False),
        sa.Column('Assignment_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ['Assignment_id'], ['Assignment.id'], ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(['User_id'], ['User.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('Assignment_id', 'User_id')
    )
    op.add_column(
        'Assignment', sa.Column('mail_task_id', sa.Unicode(), nullable=True)
    )
    op.add_column(
        'Assignment',
        sa.Column('reminder_email_time', sa.DateTime(), nullable=True)
    )

    enum = sa.Enum(
        'none',
        'assigned_only',
        'all_graders',
        name='assignmentremindertype',
    )
    enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'Assignment',
        sa.Column(
            'reminder_type',
            enum,
            server_default='none',
            nullable=False
        )
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('Assignment', 'reminder_type')
    op.drop_column('Assignment', 'reminder_email_time')
    op.drop_column('Assignment', 'mail_task_id')
    op.drop_table('AssignmentGraderDone')
    # ### end Alembic commands ###
