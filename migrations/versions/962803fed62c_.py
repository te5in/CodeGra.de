"""empty message

Revision ID: 962803fed62c
Revises: 94b1a38179a5
Create Date: 2020-03-21 13:05:35.579582

"""
import sqlalchemy as sa
import sqlalchemy_utils
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '962803fed62c'
down_revision = '94b1a38179a5'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        'Comment',
        sa.Column('id', sa.Integer(), nullable=True, primary_key=True)
    )
    op.create_unique_constraint(None, 'Comment', ['File_id', 'line'])
    op.drop_constraint('Comment_pkey', 'Comment', type_='primary')
    op.create_primary_key('Comment_pkey', 'Comment', ['id'])

    op.create_table(
        'comment_reply', sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('comment_base_id', sa.Integer(), nullable=False),
        sa.Column('deleted', sa.Boolean(), server_default='f', nullable=False),
        sa.Column('in_reply_to_id', sa.Integer(), nullable=True),
        sa.Column('author_id', sa.Integer(), nullable=False),
        sa.Column('comment', sa.Unicode(), nullable=False),
        sa.ForeignKeyConstraint(
            ['comment_base_id'],
            ['Comment.id'],
        ),
        sa.ForeignKeyConstraint(['in_reply_to_id'], ['comment_reply.id'],
                                ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['author_id'], ['User.id'],
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'comment_reply_edit',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('comment_reply_id', sa.Integer(), nullable=False),
        sa.Column('editor_id', sa.Integer(), nullable=False),
        sa.Column('new_comment', sa.Unicode(), nullable=True),
        sa.Column('old_comment', sa.Unicode(), nullable=False),
        sa.Column('was_deleted', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ['comment_reply_id'],
            ['comment_reply.id'],
        ),
        sa.ForeignKeyConstraint(['editor_id'], ['User.id'],
                                ondelete='CASCADE'),
        sa.CheckConstraint(
            'new_comment IS NOT NULL OR was_deleted',
            name='either_new_comment_or_deletion'
        ),
        sa.PrimaryKeyConstraint('id'),
    )

    bind = op.get_bind()
    bind.execute(
        """
    INSERT INTO comment_reply (created_at, updated_at, comment_base_id, in_reply_to_id, author_id, comment)
    (select NOW(), NOW(), id, NULL, "User_id", comment from "Comment");
    """
    )

    op.drop_constraint('Comment_User_id_fkey', 'Comment', type_='foreignkey')
    op.drop_column('Comment', 'comment')
    op.drop_column('Comment', 'User_id')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        'Comment',
        sa.Column('User_id', sa.INTEGER(), autoincrement=False, nullable=True)
    )
    op.add_column(
        'Comment',
        sa.Column('comment', sa.VARCHAR(), autoincrement=False, nullable=True)
    )

    bind = op.get_bind()
    bind.execute(
        """
    UPDATE "Comment" SET comment=sub.comment, "User_id"=sub.author_id
    FROM (SELECT DISTINCT ON (comment_base_id) comment, author_id, comment_base_id FROM comment_reply ORDER BY comment_base_id, created_at ASC) AS sub
    WHERE sub.comment_base_id = id
    """
    )
    op.drop_table('comment_reply_edits')
    op.drop_table('comment_reply')

    op.drop_constraint('Comment_pkey', 'Comment', type_='unique')
    op.drop_column('Comment', 'id')
    op.create_foreign_key(
        'Comment_User_id_fkey',
        'Comment',
        'User', ['User_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_primary_key('Comment_pkey', 'Comment', ['File_id', 'line'])
    # ### end Alembic commands ###
