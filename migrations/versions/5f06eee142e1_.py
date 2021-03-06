"""Improve speed AT run deletion

Revision ID: 5f06eee142e1
Revises: bfa62bee03d2
Create Date: 2020-02-19 22:43:22.175951

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '5f06eee142e1'
down_revision = 'bfa62bee03d2'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(
        'AutoTestResult_auto_test_run_id_fkey',
        'AutoTestResult',
        type_='foreignkey'
    )
    op.create_foreign_key(
        None,
        'AutoTestResult',
        'AutoTestRun', ['auto_test_run_id'], ['id'],
        ondelete='CASCADE'
    )
    op.drop_constraint(
        'AutoTestRun_auto_test_id_fkey', 'AutoTestRun', type_='foreignkey'
    )
    op.create_foreign_key(
        None,
        'AutoTestRun',
        'AutoTest', ['auto_test_id'], ['id'],
        ondelete='CASCADE'
    )
    op.drop_constraint(
        'AutoTestRunner_run_id_fkey', 'AutoTestRunner', type_='foreignkey'
    )
    op.create_foreign_key(
        None,
        'AutoTestRunner',
        'AutoTestRun', ['run_id'], ['id'],
        ondelete='CASCADE'
    )
    op.drop_constraint(
        'auto_test_step_result_auto_test_result_id_fkey',
        'auto_test_step_result',
        type_='foreignkey'
    )
    op.create_foreign_key(
        None,
        'auto_test_step_result',
        'AutoTestResult', ['auto_test_result_id'], ['id'],
        ondelete='CASCADE'
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'auto_test_step_result', type_='foreignkey')
    op.create_foreign_key(
        'auto_test_step_result_auto_test_result_id_fkey',
        'auto_test_step_result', 'AutoTestResult', ['auto_test_result_id'],
        ['id']
    )
    op.drop_constraint(None, 'AutoTestRunner', type_='foreignkey')
    op.create_foreign_key(
        'AutoTestRunner_run_id_fkey', 'AutoTestRunner', 'AutoTestRun',
        ['run_id'], ['id']
    )
    op.drop_constraint(None, 'AutoTestRun', type_='foreignkey')
    op.create_foreign_key(
        'AutoTestRun_auto_test_id_fkey', 'AutoTestRun', 'AutoTest',
        ['auto_test_id'], ['id']
    )
    op.drop_constraint(None, 'AutoTestResult', type_='foreignkey')
    op.create_foreign_key(
        'AutoTestResult_auto_test_run_id_fkey', 'AutoTestResult',
        'AutoTestRun', ['auto_test_run_id'], ['id']
    )
    # ### end Alembic commands ###
