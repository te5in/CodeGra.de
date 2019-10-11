# SPDX-License-Identifier: AGPL-3.0-only
import os
import sys
import copy
import json
import time
import uuid
import random
import signal
import string
import secrets
import datetime
import contextlib
import subprocess
import multiprocessing
import multiprocessing.managers
from urllib.error import URLError
from urllib.request import urlopen

import pytest
import flask_migrate
import sqlalchemy.orm as orm
import flask_jwt_extended as flask_jwt
from flask import _app_ctx_stack as ctx_stack
from werkzeug.local import LocalProxy

import psef
import manage
import helpers
import psef.auth as a
import psef.models as m
from helpers import create_error_template, create_user_with_perms
from lxc_stubs import lxc_stub
from psef.permissions import CoursePermission as CPerm

TESTDB = 'test_project.db'
TESTDB_PATH = "/tmp/psef/psef-{}-{}".format(TESTDB, random.random())
TEST_DATABASE_URI = 'sqlite:///' + TESTDB_PATH
LIVE_SERVER_PORT = random.randint(5001, 6001)

_DATABASE = None


def get_database_name(request):
    global _DATABASE

    if _DATABASE is None:
        _DATABASE = request.config.getoption('--postgresql'), False
        if _DATABASE[0] == 'GENERATE':
            _DATABASE = ''.join(
                x for x in secrets.token_hex(64) if x in string.ascii_lowercase
            ), True

    return _DATABASE


def pytest_addoption(parser):
    try:
        parser.addoption(
            "--postgresql",
            action="store",
            default=False,
            help="Run the test using postresql"
        )
    except ValueError:
        pass


@pytest.fixture(scope='session')
def app(request):
    """Session-wide test `Flask` application."""
    auto_test_password = uuid.uuid4().hex
    settings_override = {
        'TESTING': True,
        'DEBUG': True,
        'UPLOAD_DIR': f'/tmp/psef/uploads',
        'RATELIMIT_STRATEGY': 'moving-window',
        'RATELIMIT_HEADERS_ENABLED': True,
        'CELERY_CONFIG': {
            'BROKER_URL': 'redis:///', 'BACKEND_URL': 'redis:///'
        },
        'MIRROR_UPLOAD_DIR': f'/tmp/psef/mirror_uploads',
        'MAX_FILE_SIZE': 2 ** 20,  # 1mb
        'MAX_NORMAL_UPLOAD_SIZE': 4 * 2 ** 20,  # 4 mb
        'MAX_LARGE_UPLOAD_SIZE': 100 * 2 ** 20,  # 100mb
        'LTI_CONSUMER_KEY_SECRETS': {
            'my_lti': 'Canvas:12345678',
            'no_secret': 'Canvas:',
            'no_lms': ':12345678',
            'no_colon': '12345678',
            'unknown_lms': 'unknown:12345678',
            'blackboard_lti': 'Blackboard:12345678',
            'moodle_lti': 'Moodle:12345678',
            'brightspace_lti': 'BrightSpace:12345678',
        },
        'LTI_SECRET_KEY': 'hunter123',
        'SECRET_KEY': 'hunter321',
        'HEALTH_KEY': 'uuyahdsdsdiufhaiwueyrriu2h3',
        'CHECKSTYLE_PROGRAM': [
            "java",
            "-Dbasedir={files}",
            "-jar",
            os.path.join(os.path.dirname(__file__), '..', 'checkstyle.jar'),
            "-f",
            "xml",
            "-c",
            "{config}",
            "{files}",
        ],
        'PMD_PROGRAM': [
            os.path.join(os.path.dirname(__file__), '..', './pmd/bin/run.sh'),
            'pmd',
            '-dir',
            '{files}',
            '-failOnViolation',
            'false',
            '-format',
            'csv',
            '-shortnames',
            '-rulesets',
            '{config}',
        ],
        'MIN_PASSWORD_SCORE': 3,
        'AUTO_TEST_PASSWORD': auto_test_password,
        'AUTO_TEST_CF_EXTRA_AMOUNT': 2,
        '__S_AUTO_TEST_HOSTS': {
            f'http://127.0.0.1:{LIVE_SERVER_PORT}': {
                'password': auto_test_password, 'type': 'simple_runner'
            }
        },
        'AUTO_TEST_DISABLE_ORIGIN_CHECK': True,
        'AUTO_TEST_MAX_TIME_COMMAND': 3,
        'ADMIN_USER': None,
    }
    if request.config.getoption('--postgresql'):
        pdb, _ = get_database_name(request)

        settings_override['SQLALCHEMY_DATABASE_URI'] = f'postgresql:///{pdb}'
        settings_override['_USING_SQLITE'] = False
    else:
        settings_override['SQLALCHEMY_DATABASE_URI'] = TEST_DATABASE_URI
        settings_override['_USING_SQLITE'] = True

    settings_override['CELERY_CONFIG'] = {
        'CELERY_TASK_ALWAYS_EAGER': True,
        'CELERY_TASK_EAGER_PROPAGATES': True,
    }

    app = psef.create_app(
        settings_override, skip_celery=True, skip_perm_check=True
    )
    app.config['__S_FEATURES']['GROUPS'] = True
    app.config['FEATURES'][psef.features.Feature.GROUPS] = True

    app.config['__S_FEATURES']['AUTO_TEST'] = True
    app.config['FEATURES'][psef.features.Feature.AUTO_TEST] = True

    app.config['__S_FEATURES']['INCREMENTAL_RUBRIC_SUBMISSION'] = True
    app.config['FEATURES'][psef.features.Feature.INCREMENTAL_RUBRIC_SUBMISSION
                           ] = True

    psef.tasks.celery.conf.update({
        'task_always_eager': False,
        'task_eager_propagates': False,
    })

    # Establish an application context before running the tests.
    with app.app_context():

        class FlaskTestClientProxy(object):
            def __init__(self, app):
                self.app = app

            def __call__(self, environ, start_response):
                if (
                    _TOKENS and _TOKENS[-1] is not None and
                    'HTTP_AUTHORIZATION' not in environ
                ):
                    environ['HTTP_AUTHORIZATION'] = f'Bearer {_TOKENS[-1]}'
                return self.app(environ, start_response)

        app.wsgi_app = FlaskTestClientProxy(app.wsgi_app)

        yield app


@pytest.fixture
def test_client(app, session, assert_similar):
    client = app.test_client()

    def req(
        method,
        url,
        status_code,
        result=None,
        query=None,
        data=None,
        real_data=None,
        include_response=False,
        allow_extra=False,
        **kwargs
    ):
        setattr(ctx_stack.top, 'jwt_user', None)
        if real_data is None:
            data = json.dumps(data) if data is not None else None
            kwargs['content_type'] = 'application/json'
        else:
            data = real_data
        rv = getattr(client, method)(
            url,
            query_string=query,
            data=data,
            **kwargs,
        )
        assert rv.status_code == status_code

        if status_code == 204:
            assert rv.get_data(as_text=True) == ''
            assert result is None
            res = None
        else:
            val = json.loads(rv.get_data(as_text=True))
            res = copy.deepcopy(val)

        if result is not None:
            assert_similar(val, result)

        session.expire_all()

        if include_response:
            return res, rv
        return res

    client.req = req
    psef.limiter.reset()
    yield client


@pytest.fixture
def error_template():
    yield create_error_template()


@pytest.fixture(params=[True, False])
def boolean(request):
    yield request.param


_TOKENS = []


@pytest.fixture(autouse=True)
def clear_logged_in_user():
    setattr(ctx_stack.top, 'jwt_user', None)
    yield


@pytest.fixture
def assert_similar():
    def checker(vals, tree, cur_path):
        is_list = isinstance(tree, list)
        i = 0
        allowed_extra = False
        for k, value in enumerate(tree) if is_list else tree.items():
            if k == '__allow_extra__' and value:
                allowed_extra = True
                continue
            elif not is_list and k[0] == '?' and k[-1] == '?':
                k = k[1:-1]
                if k not in vals:
                    continue
            i += 1
            assert is_list or k in vals

            if isinstance(value, type):
                assert isinstance(vals[k], value), (
                    "Wrong type for key '{}', expected '{}', got '{}'"
                ).format('.'.join(cur_path + [str(k)]), value, vals[k])
            elif isinstance(value, list) or isinstance(value, dict):
                if isinstance(vals, dict):
                    assert k in vals
                else:
                    assert 0 <= k < len(vals)
                checker(vals[k], value, cur_path + [str(k)])
            else:
                assert vals[k] == value, (
                    "Wrong value for key '{}', expected '{}', got '{}'"
                ).format('.'.join(cur_path + [str(k)]), value, vals[k])

        if is_list:
            assert len(vals
                       ) == i, 'Length of lists is not equal: {} vs {}'.format(
                           len(vals), i
                       )
        elif not allowed_extra:
            assert len(vals) == i, 'Difference in keys: {}'.format(
                set(vals) ^ set(tree)
            )

    yield lambda val, result: checker({'top': val}, {'top': result}, [])


@pytest.fixture(autouse=True)
def logged_in():
    @contextlib.contextmanager
    def _login(user, yield_token=False):
        setattr(ctx_stack.top, 'jwt_user', None)
        if isinstance(user, str) and user == 'NOT_LOGGED_IN':
            _TOKENS.append(None)
            res = None
        else:
            _TOKENS.append(
                flask_jwt.create_access_token(identity=user.id, fresh=True)
            )
            res = user

        yield _TOKENS[-1] if yield_token else res

        _TOKENS.pop(-1)
        setattr(ctx_stack.top, 'jwt_user', None)

    yield _login
    _TOKENS.clear()

    _TOKENS.clear()


@pytest.fixture
def named_user(session, request):
    if request.param == 'NOT_LOGGED_IN':
        return 'NOT_LOGGED_IN'
    return LocalProxy(session.query(m.User).filter_by(name=request.param).one)


@pytest.fixture
def student_user(session):
    return LocalProxy(session.query(m.User).filter_by(name="Student1").one)


@pytest.fixture
def user_with_perms(session, request, course_name):
    course = session.query(m.Course).filter_by(name=course_name).one()
    yield create_user_with_perms(session, request.param, course)


@pytest.fixture
def teacher_user(session):
    return LocalProxy(session.query(m.User).filter_by(name="Robin").one)


@pytest.fixture
def ta_user(session):
    return LocalProxy(
        session.query(m.User).filter_by(name="Thomas Schaper").one
    )


@pytest.fixture
def admin_user(session):
    return LocalProxy(session.query(m.User).filter_by(name="admin").one)


@pytest.fixture
def pse_course(session):
    return session.query(m.Course
                         ).filter_by(name="Project Software Engineering").one()


@pytest.fixture
def prog_course(session):
    yield m.Course.query.filter_by(name='Programmeertalen').one()


@pytest.fixture
def inprog_course(session):
    yield m.Course.query.filter_by(name='Inleiding Programmeren').one()


@pytest.fixture
def bs_course(session):
    return session.query(m.Course).filter_by(name="Besturingssystemen").one()


@pytest.fixture
def prolog_course(session):
    return session.query(
        m.Course
    ).filter_by(name="Introductie Logisch programmeren").one()


@pytest.fixture(scope='session', autouse=True)
def db(app, request):
    """Session-wide test database."""
    if os.path.exists(TESTDB_PATH):
        os.unlink(TESTDB_PATH)

    if not request.config.getoption('--postgresql'):
        psef.models.db.create_all()
    else:
        db_name, generated = get_database_name(request)
        if generated:
            try:
                subprocess.check_output(
                    'psql -c "create database {}"'.format(db_name), shell=True
                )
            except subprocess.CalledProcessError as e:
                print(e.stdout, file=sys.stderr)
                print(e.stderr, file=sys.stderr)
            psef.models.db.create_all()

    manage.app = app
    manage.seed_force(psef.models.db)
    manage.test_data(psef.models.db)

    psef.permissions.database_permissions_sanity_check(app)

    try:
        yield psef.models.db
    finally:
        if request.config.getoption('--postgresql'):
            db_name, generated = get_database_name(request)
            if generated:
                orm.session.close_all_sessions()
                psef.models.db.engine.dispose()
                subprocess.check_call(
                    'dropdb "{}"'.format(db_name),
                    shell=True,
                    stdout=sys.stdout,
                    stderr=sys.stderr
                )
        else:
            os.unlink(TESTDB_PATH)


@pytest.fixture(params=[True])
def use_transaction(request):
    yield request.param


@pytest.fixture(autouse=True)
def session(app, db, use_transaction):
    """Creates a new database session for a test."""
    connection = db.engine.connect()
    if use_transaction:
        transaction = connection.begin()

    options = dict(bind=connection, binds={}, autoflush=False)
    session = db.create_scoped_session(options=options)

    old_ses = psef.models.db.session
    psef.models.db.session = session

    try:
        yield session
    finally:
        psef.models.db.session = old_ses
        print(old_ses)

        if use_transaction:
            transaction.rollback()

        try:
            session.remove()
            connection.close()
        except:
            import traceback
            traceback.print_exc(file=sys.stderr)
            raise

        if not use_transaction:
            db.drop_all()
            sys.setrecursionlimit(5000)
            psef.models.db.create_all()
            manage.app = app
            manage.seed_force(psef.models.db)
            assert manage.test_data(psef.models.db) != 1
            psef.permissions.database_permissions_sanity_check(app)


@pytest.fixture
def monkeypatch_celery(app, monkeypatch):
    psef.tasks.celery.conf.task_always_eager = True
    psef.tasks.celery.conf.task_eager_propagates = True
    yield
    psef.tasks.celery.conf.task_always_eager = False
    psef.tasks.celery.conf.task_eager_propagates = False


@pytest.fixture(params=['Programmeertalen'])
def course_name(request):
    yield request.param


@pytest.fixture
def course(session, course_name):
    yield LocalProxy(session.query(m.Course).filter_by(name=course_name).first)


DESCRIBE_HOOKS = []


@pytest.fixture
def describe():
    @contextlib.contextmanager
    def inner(name):
        print()
        sep = '+={}=+'.format('=' * len(name))
        print(sep)
        print('|', name, '|')
        print(sep)
        print()
        yield
        for i, h in enumerate(DESCRIBE_HOOKS):
            h()

    yield inner

    DESCRIBE_HOOKS.clear()


@pytest.fixture(params=[False])
def state_is_hidden(request):
    yield request.param


@pytest.fixture(params=[False])
def with_works(request):
    yield request.param


@pytest.fixture(params=['new'])
def assignment(course_name, state_is_hidden, session, request, with_works):
    course = m.Course.query.filter_by(name=course_name).one()
    state = (
        m._AssignmentStateEnum.hidden
        if state_is_hidden else m._AssignmentStateEnum.open
    )
    assig = m.Assignment(
        name='TEST COURSE',
        state=state,
        course=course,
        deadline=datetime.datetime.utcnow() +
        datetime.timedelta(days=1 if request.param == 'new' else -1)
    )
    session.add(assig)
    session.commit()

    if with_works:
        names = ['Student1', 'Student2', 'Student3', 'Œlµo']
        if with_works != 'single':
            names += names
        for uname in names:
            user = m.User.query.filter_by(name=uname).one()
            work = m.Work(assignment=assig, user=user)
            session.add(work)
        session.commit()

    yield assig


@pytest.fixture
def filename(request):
    yield request.param


@pytest.fixture
def stub_function_class():
    class StubFunction:
        def __init__(self, ret_func=lambda: None, with_args=False):
            self.args = []
            self.kwargs = []
            self.rets = []
            self.ret_func = ret_func
            self.with_args = with_args
            self.call_dates = []
            DESCRIBE_HOOKS.append(self.reset)

        @property
        def all_args(self):
            def merge(args, kwargs):
                res = {idx: val for idx, val in enumerate(args)}
                res.update(kwargs)
                return res

            return [merge(a, k) for a, k in zip(self.args, self.kwargs)]

        def __call__(self, *args, **kwargs):
            self.args.append(args)
            self.kwargs.append(kwargs)
            self.call_dates.append(datetime.datetime.utcnow())

            if self.with_args:
                self.rets.append(self.ret_func(*args, **kwargs))
            else:
                self.rets.append(self.ret_func())
            return self.rets[-1]

        @property
        def called(self):
            return len(self.args) > 0

        def reset(self):
            self.args = []
            self.kwargs = []
            self.rets = []
            self.call_dates = []

    yield StubFunction


@pytest.fixture
def assignment_real_works(
    filename,
    test_client,
    logged_in,
    assignment,
):
    res = []
    for name in ['Student1', 'Student2', 'Œlµo']:
        user = m.User.query.filter_by(name=name).one()
        with logged_in(user):
            res.append(
                test_client.req(
                    'post',
                    f'/api/v1/assignments/{assignment.id}/submission',
                    201,
                    real_data={
                        'file': (
                            f'{os.path.dirname(__file__)}/../'
                            f'test_data/test_linter/{filename}',
                            os.path.basename(os.path.realpath(filename))
                        )
                    }
                )
            )

    yield assignment, res[0]


@pytest.fixture
def live_server(app):
    p = None

    def stop():
        if p is None:
            return

        os.kill(p.pid, signal.SIGINT)
        try:
            p.join(4)
        except:
            p.terminate()
            p.join()

    def start(get_stop=False):
        nonlocal p

        def _inner():
            app.run(
                host='localhost',
                port=LIVE_SERVER_PORT,
                use_reloader=False,
                threaded=False
            )

        p = multiprocessing.Process(target=_inner)
        p.start()
        url = f'http://localhost:{LIVE_SERVER_PORT}'

        for _ in range(15):
            try:
                urlopen(f'{url}/api/v1/about')
            except URLError:
                time.sleep(1)
                pass
            else:
                break
        else:
            stop()
            assert False, "Server on {} could not be reached".format(url)

        if get_stop:
            return url, stop
        return url

    try:
        yield start
    finally:
        stop()


@pytest.fixture
def stubmailer(monkeypatch):
    class StubMailer():
        def __init__(self):
            self.msg = None
            self.do_raise = False
            self.called = 0
            self.args = []
            self.kwargs = []

        def send(self, msg):
            self.called += 1
            self.msg = msg
            self.args.append((msg, ))
            if self.do_raise:
                raise Exception

        def reset(self):
            self.msg = None
            self.args = []
            self.called = 0

    mailer = StubMailer()

    monkeypatch.setattr(psef.mail, 'mail', mailer)

    yield mailer


@pytest.fixture
def tomorrow():
    yield datetime.datetime.utcnow() + datetime.timedelta(days=1)
