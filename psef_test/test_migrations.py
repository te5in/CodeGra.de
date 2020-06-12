import os
import re
import uuid
import tempfile
import subprocess
import configparser
from os import path
from collections import namedtuple

import pytest
import alembic
from sqlalchemy import text, create_engine
from flask_migrate import Migrate
from alembic.config import Config as AlembicConfig
from alembic.script import ScriptDirectory

import psef
import migrations

MIGRATION_PATH = path.join(path.dirname(__file__), '..', 'migrations')

ALL_MIGRATIONS = [
    x.split('.', 1)[0].split('_', 1)[0]
    for x in os.listdir(path.join(MIGRATION_PATH, 'versions'))
    if x.endswith('.py')
]

MIGRATIONS_TEST_DIR = path.join(path.dirname(__file__), 'migrations')
ALL_MIGRATION_TESTS = [
    x.split('.', 1)[0].split('_')[1] for x in os.listdir(MIGRATIONS_TEST_DIR)
    if (
        x not in ('__init__.py', '__pycache__') and
        (x.endswith('.py') or path.isdir(path.join(MIGRATIONS_TEST_DIR, x)))
    )
]
assert ALL_MIGRATION_TESTS

ALL_TESTED_MIGRATIONS = []


def fill_all_tested_migrations():
    for migration in ALL_MIGRATIONS:
        if migration in ALL_MIGRATION_TESTS:
            ALL_TESTED_MIGRATIONS.append(migration)
            ALL_MIGRATION_TESTS.remove(migration)
            # Make sure pytest rewrites the assertions in these test files
            mod_name = 'migrations.migration_{}'.format(migration)
            pytest.register_assert_rewrite(mod_name)


fill_all_tested_migrations()
assert not ALL_MIGRATION_TESTS, 'Found unknown migrations'
assert ALL_TESTED_MIGRATIONS

WHITESPACE_REGEX = re.compile(r'\s+')
FreshDatabase = namedtuple('FreshDatabase', ['engine', 'name', 'db_name'])


@pytest.fixture
def migration_app(make_app_settings, fresh_database):
    app = psef.create_app(
        make_app_settings(database=fresh_database.name),
        skip_celery=True,
        skip_perm_check=True
    )
    Migrate(app, psef.models.db, compare_type=True)
    yield app


@pytest.fixture
def fresh_database():
    db_name = f'migration_test_db_{uuid.uuid4()}'.replace('-', '')
    subprocess.check_output(['psql', '-c', f'create database "{db_name}"'])
    try:
        subprocess.check_output([
            'psql', db_name, '-c', 'create extension "uuid-ossp"'
        ])
        subprocess.check_output([
            'psql', db_name, '-c', 'create extension "citext"'
        ])
        db_string = f'postgresql:///{db_name}'
        engine = create_engine(db_string)
        yield FreshDatabase(engine=engine, name=db_string, db_name=db_name)
    finally:
        engine.dispose()
        subprocess.check_output(['psql', '-c', f'drop database "{db_name}"'])


@pytest.fixture
def alembic_config(fresh_database):
    ini = configparser.ConfigParser()
    ini.read(path.join(MIGRATION_PATH, 'alembic.ini'))
    ini.set('alembic', 'script_location', path.join(MIGRATION_PATH))
    ini.set('alembic', 'sqlalchemy.url', fresh_database.name)

    with tempfile.TemporaryDirectory() as tmp_dir:
        res = path.join(tmp_dir, 'alembic.ini')
        with open(res, 'w') as f:
            ini.write(f)
        yield res


def list_migrations(alembic_config, head):
    print(alembic_config)
    config = AlembicConfig(alembic_config)
    script = ScriptDirectory.from_config(config)
    migrations = [
        x.revision for x in script.walk_revisions(base='base', head=head)
    ]
    migrations.reverse()
    return migrations


@pytest.fixture
def upgrade(migration_app):
    def inner(alembic_config, migration):
        with migration_app.app_context():
            config = AlembicConfig(alembic_config)
            alembic.command.upgrade(config, migration, sql=False, tag=None)

    yield inner


@pytest.fixture
def downgrade(migration_app):
    def inner(alembic_config, migration):
        with migration_app.app_context():
            config = AlembicConfig(alembic_config)
            alembic.command.downgrade(config, migration, sql=False, tag=None)

    yield inner


def get_schema(app, db):
    with app.app_context():
        result = list(
            db.engine.execute(
                text(
                    '''
            SELECT type, name, tbl_name, sql
            FROM sqlite_master
            ORDER BY type, name, tbl_name
            '''
                )
            )
        )

    return {(x[0], x[1], x[2]): x[3] for x in result}


def assert_schemas_equal(left, right):
    for k, v in left.items():
        if k not in right:
            raise AssertionError(
                'Left contained {} but right did not'.format(k)
            )
        if not ddl_equal(v, right[k]):
            raise AssertionError(
                'Schema for {} did not match:\nLeft:\n{}\nRight:\n{}'.format(
                    k, v, right[k]
                )
            )
        right.pop(k)

    if right:
        raise AssertionError(
            'Right had additional tables: {}'.format(list(right.keys()))
        )


def ddl_equal(left, right):
    '''Check the "tokenized" DDL is equivalent because, because sometimes
        Alembic schemas append columns on the same line to the DDL comes out
        like:

        column1 TEXT NOT NULL, column2 TEXT NOT NULL

        and SQLAlchemy comes out:

        column1 TEXT NOT NULL,
        column2 TEXT NOT NULL
    '''
    # ignore the autoindex cases
    if left is None and right is None:
        return True

    left = [x for x in WHITESPACE_REGEX.split(left) if x]
    right = [x for x in WHITESPACE_REGEX.split(right) if x]

    # Strip commas and quotes
    left = [x.replace("\"", "").replace(",", "") for x in left]
    right = [x.replace("\"", "").replace(",", "") for x in right]

    return sorted(left) == sorted(right)


@pytest.mark.parametrize('migration', ALL_TESTED_MIGRATIONS)
def test_upgrade_with_data(
    alembic_config, migration, fresh_database, migration_app, upgrade
):
    migrations = list_migrations(alembic_config, migration)
    if len(migrations) == 1:
        # Degenerate case where there is no data for the first migration
        return

    # Upgrade to one migration before the target stored in `migration`
    last_migration = migrations[-2]
    upgrade(alembic_config, last_migration)

    # Dynamic module import
    mod_name = 'migrations.migration_{}'.format(migration)
    mod = __import__(mod_name, fromlist=['UpgradeTester'])
    if not mod.UpgradeTester.do_test():
        pytest.skip('This upgrade is not tested')

    # Load the test data
    setup_sql = path.join(
        MIGRATIONS_TEST_DIR, f'migration_{migration}', 'setup_upgrade.sql'
    )
    if path.isfile(setup_sql):
        subprocess.check_call(
            [
                'psql', '-d', fresh_database.db_name, '--set=ON_ERROR_STOP=1',
                '--set=ECHO=queries', '-f', setup_sql
            ],
            stderr=subprocess.STDOUT,
            text=True,
        )

    upgrade_tester = mod.UpgradeTester(db=fresh_database)
    upgrade_tester.load_data()

    # Upgrade to the target
    upgrade(alembic_config, migration)

    # Make sure it applied "cleanly" for some definition of clean
    upgrade_tester.check_upgrade()


@pytest.mark.parametrize('migration', ALL_TESTED_MIGRATIONS)
def test_downgrade_with_data(
    alembic_config, migration, fresh_database, downgrade, upgrade
):
    # Upgrade to the target
    upgrade(alembic_config, migration)

    # Dynamic module import
    mod_name = 'migrations.migration_{}'.format(migration)
    mod = __import__(mod_name, fromlist=['DowngradeTester'])
    if not mod.DowngradeTester.do_test():
        pytest.skip('This upgrade is not tested')

    # Load the test data
    setup_sql = path.join(
        MIGRATIONS_TEST_DIR, f'migration_{migration}', 'setup_downgade.sql'
    )
    if path.isfile(setup_sql):
        subprocess.check_call(
            [
                'psql', '-d', fresh_database.db_name, '--set=ON_ERROR_STOP=1',
                '--set=ECHO=queries', '-f', setup_sql
            ],
            stderr=subprocess.STDOUT,
            text=True,
        )

    # Load the test data
    downgrade_tester = mod.DowngradeTester(db=fresh_database)
    downgrade_tester.load_data()

    # Downgrade to previous migration
    downgrade(alembic_config, '-1')

    # Make sure it applied "cleanly" for some definition of clean
    downgrade_tester.check_downgrade()
