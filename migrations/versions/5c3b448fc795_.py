"""Add columns and permissions needed for plagiarism detection

Revision ID: 5c3b448fc795
Revises: 729a1509580b
Create Date: 2018-09-09 14:37:24.958758

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '5c3b448fc795'
down_revision = '729a1509580b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        'PlagiarismRun', sa.Column('id', sa.Integer(), nullable=False),
        sa.Column(
            'state',
            sa.Enum('running', 'done', 'crashed', name='plagiarismtate'),
            nullable=False
        ), sa.Column('log', sa.Unicode(), nullable=True),
        sa.Column('json_config', sa.Unicode(), nullable=True),
        sa.Column('assignment_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ['assignment_id'],
            ['Assignment.id'],
        ), sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'PlagiarismCase', sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('work1_id', sa.Integer(), nullable=True),
        sa.Column('work2_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('plagiarism_run_id', sa.Integer(), nullable=True),
        sa.Column('match_avg', sa.Float(), nullable=False),
        sa.Column('match_max', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(
            ['plagiarism_run_id'], ['PlagiarismRun.id'], ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(['work1_id'], ['Work.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['work2_id'], ['Work.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'PlagiarismMatch', sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('file1_id', sa.Integer(), nullable=True),
        sa.Column('file2_id', sa.Integer(), nullable=True),
        sa.Column('file1_start', sa.Integer(), nullable=False),
        sa.Column('file1_end', sa.Integer(), nullable=False),
        sa.Column('file2_start', sa.Integer(), nullable=False),
        sa.Column('file2_end', sa.Integer(), nullable=False),
        sa.Column('plagiarism_case_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ['file1_id'],
            ['File.id'],
        ), sa.ForeignKeyConstraint(
            ['file2_id'],
            ['File.id'],
        ),
        sa.ForeignKeyConstraint(
            ['plagiarism_case_id'], ['PlagiarismCase.id'], ondelete='CASCADE'
        ), sa.PrimaryKeyConstraint('id')
    )

    conn = op.get_bind()
    conn.execute(
        text(
            """
    INSERT INTO "Permission" (name, default_value, course_permission)
    SELECT 'can_view_plagiarism', false, true WHERE NOT EXISTS
        (SELECT 1 FROM "Permission" WHERE name = 'can_view_plagiarism')
    """
        )
    )
    conn.execute(
        text(
            """
    INSERT INTO "Permission" (name, default_value, course_permission)
    SELECT 'can_manage_plagiarism', false, true WHERE NOT EXISTS
        (SELECT 1 FROM "Permission" WHERE name = 'can_manage_plagiarism')
    """
        )
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('PlagiarismMatch')
    op.drop_table('PlagiarismCase')
    op.drop_table('PlagiarismRun')
    # ### end Alembic commands ###
