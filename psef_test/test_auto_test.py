# SPDX-License-Identifier: AGPL-3.0-only
import io
import os
import copy
import json
import time
import uuid
import shutil
import getpass
import tempfile
import threading
from datetime import datetime, timedelta
from textwrap import dedent

import lxc
import pytest
import requests
import pytest_cov

import psef
import helpers
import psef.models as m
import cg_worker_pool
import requests_stubs
from psef.exceptions import APICodes, APIException


@pytest.fixture
def monkeypatch_for_run(monkeypatch, lxc_stub, stub_function_class):
    old_run_command = psef.auto_test.StartedContainer._run_command
    psef.auto_test._STOP_CONTAINERS.clear()

    monkeypatch.setattr(
        psef.auto_test, '_SYSTEMD_WAIT_CMD',
        ['python', '-c', 'import random; exit(random.randint(0, 1))']
    )

    def new_run_command(self, cmd_user):
        signal_start = psef.auto_test.StartedContainer._signal_start
        cmd, user = cmd_user
        if cmd[0] in {'adduser', 'usermod', 'deluser', 'sudo', 'apt'}:
            signal_start()
            return 0
        elif cmd == ['grep', '-c', getpass.getuser(), '/etc/sudoers']:
            signal_start()
            return 1
        elif '/etc/sudoers' in cmd:
            signal_start()
            return 0
        return old_run_command(self, cmd_user)

    monkeypatch.setattr(psef.auto_test, 'CODEGRADE_USER', getpass.getuser())
    monkeypatch.setattr(
        psef.helpers, 'ensure_on_test_server', stub_function_class()
    )

    monkeypatch.setattr(
        psef.auto_test.StartedContainer, '_run_command', new_run_command
    )
    monkeypatch.setattr(lxc, 'Container', lxc_stub)
    monkeypatch.setattr(
        psef.auto_test, '_get_amount_cpus', stub_function_class(lambda: 1)
    )
    monkeypatch.setattr(
        cg_worker_pool, '_make_process',
        stub_function_class(
            lambda *args, **kwargs: threading.Thread(*args, **kwargs),
            with_args=True
        )
    )
    monkeypatch.setattr(
        psef.auto_test.AutoTestRunner, '_get_amount_of_needed_workers',
        stub_function_class(lambda: 1)
    )
    monkeypatch.setattr(
        psef.tasks, 'check_heartbeat_auto_test_run', stub_function_class()
    )
    monkeypatch.setattr(
        psef.tasks, 'stop_auto_test_run', stub_function_class()
    )
    monkeypatch.setattr(psef.auto_test, '_REQUEST_TIMEOUT', 0.1)


@pytest.fixture
def monkeypatch_broker(monkeypatch):
    monkeypatch.setattr(psef.helpers, 'BrokerSession', requests_stubs.Session)
    yield


@pytest.fixture(autouse=True)
def monkeypatch_os_exec(monkeypatch):
    def flush_and_call(func):
        def inner(*args, **kwargs):
            pytest_cov.embed.cleanup()
            func(*args, **kwargs)

        return inner

    for func in ['execve', 'execvpe', 'execvp', '_exit']:
        orig = getattr(os, func)
        monkeypatch.setattr(os, func, flush_and_call(orig))
    yield


@pytest.fixture
def basic(logged_in, admin_user, test_client, session):
    print(m.User.query.all())
    with logged_in(admin_user):
        course = helpers.create_course(test_client)
        assig_id = helpers.create_assignment(
            test_client,
            course,
            deadline=datetime.utcnow() + timedelta(days=30)
        )['id']
        teacher = helpers.create_user_with_role(session, 'Teacher', [course])
        student = helpers.create_user_with_role(session, 'Student', [course])
    yield course, assig_id, teacher, student


def test_create_auto_test(test_client, basic, logged_in, describe):
    course, assig_id, teacher, student = basic

    with describe('Creating a auto test as student is not possible'
                  ), logged_in(student):
        test_client.req(
            'post',
            '/api/v1/auto_tests/',
            data={'assignment_id': assig_id},
            status_code=403,
            result=helpers.create_error_template(),
        )

    with describe('Creating a simple test'), logged_in(teacher):
        test_client.req(
            'post',
            '/api/v1/auto_tests/',
            data={'assignment_id': assig_id},
            status_code=200,
            result={
                'id': int,
                'fixtures': [],
                'setup_script': '',
                'run_setup_script': '',
                'finalize_script': '',
                'sets': [],
                'assignment_id': assig_id,
                'grade_calculation': None,
                'runs': [],
            }
        )

    with describe('Creating another test in the same assignment fails'
                  ), logged_in(teacher):
        test_client.req(
            'post',
            '/api/v1/auto_tests/',
            data={'assignment_id': assig_id},
            status_code=409,
            result=helpers.create_error_template(),
        )


def test_create_auto_test_set(basic, test_client, logged_in, describe):
    with describe('setup'):
        course, assig_id, teacher, student = basic
        with logged_in(teacher):
            test = helpers.create_auto_test(test_client, assig_id, 0, 0)
            rubric = test_client.req(
                'put',
                f'/api/v1/assignments/{assig_id}/rubrics/',
                200,
                data=helpers.get_simple_rubric()
            )

        url = f'/api/v1/auto_tests/{test["id"]}'

    with describe('Students cannot create suites'), logged_in(student):
        test_client.req('post', f'{url}/sets/', 403)

        with describe('No set should be created'), logged_in(teacher):
            test_client.req('get', url, 200, result=test)

    with describe('Teacher can create sets'), logged_in(teacher):
        test_client.req('post', f'{url}/sets/', 200)

        with describe('Created sets should have correct default values'):
            test_client.req(
                'get',
                url,
                200,
                result={
                    **test,
                    'sets': [
                        *test['sets'],
                        {'id': int, 'suites': [], 'stop_points': 0}
                    ],
                }
            )


def test_create_auto_test_suite(basic, test_client, logged_in, describe):
    course, assig_id, teacher, student = basic

    with describe('setup'), logged_in(teacher):
        test = helpers.create_auto_test(test_client, assig_id, 1, 0)
        rubric = test_client.req(
            'put',
            f'/api/v1/assignments/{assig_id}/rubrics/',
            200,
            data=helpers.get_simple_rubric()
        )
        set_id = test['sets'][0]['id']
        url = f'/api/v1/auto_tests/{test["id"]}'

    with describe('students should not be able to create suite'
                  ), logged_in(student):
        test_client.req('patch', f'{url}/sets/{set_id}/suites/', 403)
        with describe('No suite should be created'), logged_in(teacher):
            test_client.req('get', url, 200, result=test)

    with describe('teachers should be able to create empty suites'
                  ), logged_in(teacher):
        test_client.req(
            'patch',
            f'{url}/sets/{set_id}/suites/',
            200,
            data={
                'steps': [],
                'rubric_row_id': rubric[0]['id'],
                'network_disabled': False,
            }
        )

        test_client.req(
            'get',
            url,
            200,
            {
                **test,
                'sets': [{
                    **test['sets'][0],
                    'suites': [{
                        'id': int,
                        'rubric_row': {**rubric[0], 'locked': 'auto_test'},
                        'network_disabled': False,
                        'steps': [],
                        # This is set in the conftest.py
                        'command_time_limit': 3,
                    }],
                }]
            }
        )

    with describe('rubric rows cannot be connected to two suites'
                  ), logged_in(teacher):
        test_client.req(
            'patch',
            f'{url}/sets/{set_id}/suites/',
            409,
            data={
                'steps': [],
                'rubric_row_id': rubric[0]['id'],
                'network_disabled': False,
            }
        )


def test_delete_auto_test(basic, test_client, logged_in, describe):
    with describe('setup'):
        course, assig_id, teacher, student = basic
        with logged_in(teacher):
            test = helpers.create_auto_test(test_client, assig_id)
        url = f'/api/v1/auto_tests/{test["id"]}'

    with describe('Students cannot delete auto tests'):
        with logged_in(student):
            test_client.req('delete', url, 403)
        with logged_in(teacher):
            test_client.req('get', url, 200, result=test)

    with describe('Teachers can delete auto tests'), logged_in(teacher):
        test_client.req('delete', url, 204)
        test_client.req('get', url, 404)


def test_view_auto_test(basic, test_client, logged_in, describe):
    with describe('setup'):
        course, assig_id, teacher, student = basic
        with logged_in(teacher):
            test = helpers.create_auto_test(test_client, assig_id)
        url = f'/api/v1/auto_tests/{test["id"]}'

        def update_state(state):
            with logged_in(teacher):
                test_client.req(
                    'patch',
                    f'/api/v1/assignments/{assig_id}',
                    200,
                    data={'state': state}
                )

        update_state('open')

    with describe('Students cannot see auto test before deadline'
                  ), logged_in(student):
        test_client.req('get', url, 403)
        test_client.req(
            'get',
            f'/api/v1/assignments/{assig_id}',
            200,
            result={
                '__allow_extra__': True,
                # You are allowed to see the id.
                'auto_test_id': test['id'],
            }
        )

    with describe('Students can se auto test after deadline'):
        update_state('done')

        with logged_in(student):
            test_client.req('get', url, 200, result=test)
            test_client.req(
                'get',
                f'/api/v1/assignments/{assig_id}',
                200,
                result={
                    '__allow_extra__': True,
                    'auto_test_id': test['id'],
                }
            )


def test_start_auto_test_before_complete(
    basic, test_client, logged_in, describe, session, monkeypatch_celery,
    monkeypatch_broker
):
    test = url = None

    def update_test(**new_data):
        nonlocal test, url
        res = rv = None

        if new_data:
            res, rv = test_client.req(
                'patch',
                url,
                new_data.pop('error', 200),
                data=new_data,
                include_response=True,
            )

        with logged_in(teacher):
            old_test = test
            test = test_client.req('get', url, 200)
            assert test['id'] == old_test['id']

        return res, rv

    def start_run(error):
        return test_client.req('post', f'{url}/runs/', error)

    with describe('setup'):
        course, assig_id, teacher, student = basic
        with logged_in(teacher):
            test = helpers.create_auto_test(
                test_client,
                assig_id,
                amount_sets=2,
                amount_suites=2,
                grade_calculation=None,
            )
            url = f'/api/v1/auto_tests/{test["id"]}'
            update_test()

    with describe('no grade calculator'), logged_in(teacher):
        err = start_run(409)
        assert 'no grade_calculation' in err['message']
        update_test(grade_calculation='full')

    with describe('no submissions'), logged_in(teacher):
        err = start_run(409)
        assert 'there are no submissions' in err['message']
        helpers.create_submission(test_client, assig_id)

    with describe('already has a run'), logged_in(teacher):
        start_run(200)
        err = start_run(409)
        assert 'which has runs' in err['message']
        t = m.AutoTest.query.get(test['id'])
        t.runs = []
        session.commit()

    with describe('weight of zero'), logged_in(teacher):
        suite = next(t.all_suites)
        for step in suite.steps:
            step.weight = 0
        session.commit()
        err = start_run(409)
        assert 'has zero amount of points' in err['message']

        suite.steps[0].weight = 1
        session.commit()

    with describe('no steps in some suites'), logged_in(teacher):
        suite.steps = []
        session.commit()
        err = start_run(409)
        assert 'has no steps in some suites' in err['message']

    with describe('no suites'), logged_in(teacher):
        for s in t.sets:
            s.suites = []
        session.commit()
        err = start_run(409)
        assert 'has no suites' in err['message']

    with describe('no sets'), logged_in(teacher):
        t.sets = []
        session.commit()
        err = start_run(409)
        assert 'has no sets' in err['message']


def test_update_auto_test(
    basic, test_client, logged_in, describe, assert_similar, app
):
    test = url = None

    def update_test(**new_data):
        nonlocal test, url
        res = rv = None

        if new_data:
            data = {}
            for key in list(new_data.keys()):
                if key.startswith('fixture') and key != 'fixtures':
                    data[key] = new_data.pop(key)
            data['json'] = (
                io.BytesIO(
                    json.dumps(
                        {**test, **new_data, 'has_new_fixtures': bool(data)}
                    ).encode()
                ), 'json'
            )

            res, rv = test_client.req(
                'patch',
                url,
                new_data.pop('error', 200),
                real_data=data,
                include_response=True,
            )

        with logged_in(teacher):
            old_test = test
            test = test_client.req('get', url, 200)
            assert test['id'] == old_test['id']

        return res, rv

    with describe('setup'):
        course, assig_id, teacher, student = basic

        with logged_in(teacher):
            # We need to make a submission, otherwise we cannot start tests
            helpers.create_submission(test_client, assig_id)

            test = helpers.create_auto_test(test_client, assig_id)
            url = f'/api/v1/auto_tests/{test["id"]}'
            update_test()

    with describe('students cannot update'), logged_in(student):
        update_test(error=403)

    with describe('update grade calculation'), logged_in(teacher):
        assert test['grade_calculation'] is None
        update_test(grade_calculation='not valid', error=404)
        assert test['grade_calculation'] is None
        update_test(grade_calculation='full')
        assert test['grade_calculation'] == 'full'
        update_test(grade_calculation='partial')

    with describe('update setup script'), logged_in(teacher):
        new_script = uuid.uuid4().hex
        update_test(setup_script=new_script)
        assert test['setup_script'] == new_script
        update_test(setup_script='')
        assert test['setup_script'] == ''

    with describe('run setup script'), logged_in(teacher):
        new_script = uuid.uuid4().hex
        update_test(run_setup_script=new_script)
        assert test['run_setup_script'] == new_script
        update_test(run_setup_script='')
        assert test['run_setup_script'] == ''

    with describe('add fixtures'), logged_in(teacher):
        update_test(fixture1=(io.BytesIO(b'hello'), 'file1'))
        fixture, = test['fixtures']
        assert_similar(fixture, {'hidden': True, 'id': int, 'name': 'file1'})

        res = test_client.get(f'{url}/fixtures/{fixture["id"]}')
        assert res.status_code == 200
        assert res.get_data(as_text=True) == 'hello'

        with logged_in(student):
            # Fixture is hidden so student may not see it
            res = test_client.get(f'{url}/fixtures/{fixture["id"]}')
            assert res.status_code == 403

        test_client.req('delete', f'{url}/fixtures/{fixture["id"]}/hide', 204)

        with logged_in(student):
            # Fixture is not hidden anymore so student may see it
            res = test_client.get(f'{url}/fixtures/{fixture["id"]}')
            assert res.status_code == 200

        update_test(fixtures=[])
        assert test['fixtures'] == []

    with describe('upload same fixture twice'), logged_in(teacher):
        update_test(fixture1=(io.BytesIO(b'hello1'), 'file2'))
        _, rv = update_test(fixture1=(io.BytesIO(b'hello2'), 'file2'))
        assert 'Warning' in rv.headers
        assert 'were renamed' in rv.headers['Warning']

        fixture1, fixture2 = test['fixtures']
        assert_similar(
            test['fixtures'],
            [{'hidden': True, 'id': int, 'name': 'file2'},
             {'hidden': True, 'id': int, 'name': 'file2 (1)'}]
        )

        res = test_client.get(f'{url}/fixtures/{fixture1["id"]}')
        assert res.get_data(as_text=True) == 'hello1'

        res = test_client.get(f'{url}/fixtures/{fixture2["id"]}')
        assert res.get_data(as_text=True) == 'hello2'

    with describe('cannot update when there are runs'), logged_in(teacher):
        update_test(error=200)
        t = m.AutoTest.query.get(test['id'])
        with app.test_request_context('/'):
            t.start_test_run()
        update_test(error=409)


@pytest.mark.parametrize('use_transaction', [False], indirect=True)
def test_run_auto_test(
    monkeypatch_celery, monkeypatch_broker, basic, test_client, logged_in,
    describe, live_server, lxc_stub, monkeypatch, app, session,
    stub_function_class, assert_similar, monkeypatch_for_run
):
    tmpdir = None

    with describe('setup'):
        course, assig_id, teacher, student1 = basic
        student2 = helpers.create_user_with_role(session, 'Student', [course])

        with logged_in(teacher):
            test = helpers.create_auto_test(
                test_client,
                assig_id,
                amount_sets=2,
                amount_suites=2,
                amount_fixtures=1,
                stop_points=[0.5, None],
                grade_calculation='partial',
            )
            test_client.req(
                'patch',
                f'/api/v1/assignments/{assig_id}',
                200,
                data={'state': 'open'}
            )
        url = f'/api/v1/auto_tests/{test["id"]}'

        _run_student = psef.auto_test._run_student

        monkeypatch.setattr(
            psef.auto_test, '_get_home_dir',
            stub_function_class(lambda: tmpdir)
        )

        def next_student(*args, **kwargs):
            nonlocal tmpdir

            with tempfile.TemporaryDirectory() as tdir:
                tmpdir = tdir
                for inner in ['/student', '/fixtures']:
                    shutil.copytree(upper_tmpdir + inner, tdir + inner)
                return _run_student(*args, **kwargs)

        monkeypatch.setattr(psef.auto_test, '_run_student', next_student)

        with logged_in(student1):
            work1 = helpers.create_submission(test_client, assig_id)
            with logged_in(teacher):
                test_client.req(
                    'patch',
                    f'/api/v1/submissions/{work1["id"]}',
                    200,
                    data={'grade': 5.0}
                )
        with logged_in(student2):
            prog = """
            import sys
            if len(sys.argv) > 1:
                print("hello {}!".format(sys.argv[1]))
            else:
                print("hello stranger!")
            """
            work2 = helpers.create_submission(
                test_client,
                assig_id,
                submission_data=(io.BytesIO(dedent(prog).encode()), 'test.py')
            )

    with describe('start_auto_test'
                  ), tempfile.TemporaryDirectory() as upper_tmpdir:
        tmpdir = upper_tmpdir

        t = m.AutoTest.query.get(test['id'])
        with logged_in(teacher):
            test_client.req(
                'post',
                f'{url}/runs/',
                200,
                data={
                    'continuous_feedback_run': False,
                }
            )
            session.commit()
        run = t.test_run

        live_server_url = live_server()
        psef.auto_test.start_polling(app.config, repeat=False)

        with logged_in(teacher, yield_token=True) as token:
            response = requests.get(
                f'{live_server_url}{url}/runs/{run.id}',
                headers={'Authorization': f'Bearer {token}'}
            )
            response.raise_for_status()
            assert_similar(
                response.json(), {
                    'id': run.id,
                    'created_at': str,
                    'state': 'done',
                    'results': [object, object],
                    'setup_stderr': str,
                    'setup_stdout': str,
                    'is_continuous': False,
                }
            )

        res1 = session.query(m.AutoTestResult).filter_by(work_id=work1['id']
                                                         ).one().id
        res2 = session.query(m.AutoTestResult).filter_by(work_id=work2['id']
                                                         ).one().id

        with logged_in(student1):
            # A student cannot see results before the assignment is done
            test_client.req('get', f'{url}/runs/{run.id}/results/{res1}', 403)

        with logged_in(teacher):
            # A teacher can see the results before done
            test_client.req('get', f'{url}/runs/{run.id}/results/{res1}', 200)
            test_client.req(
                'patch',
                f'/api/v1/assignments/{assig_id}',
                200,
                data={'state': 'done'}
            )

        with logged_in(student1):
            # A student cannot see the results of another student
            test_client.req('get', f'{url}/runs/{run.id}/results/{res2}', 403)

            # You should be able too see your own results
            res = test_client.req(
                'get',
                f'{url}/runs/{run.id}/results/{res1}',
                200,
                result={
                    'id': int, 'points_achieved': 0, '__allow_extra__': True
                }
            )
            # There should be only two results as all other tests should be
            # skipped
            len(res['step_results']) == 2
            test_client.req(
                'get',
                f'/api/v1/submissions/{work1["id"]}',
                200,
                result={
                    '__allow_extra__': True,
                    'grade': 5.0,
                    'grade_overridden': True,
                }
            )

        with logged_in(student2):
            # You should be able too see your own results
            res = test_client.req(
                'get',
                f'{url}/runs/{run.id}/results/{res2}',
                200,
                result={
                    # The last two run programs should time out, so 2 * 3 + 2 *
                    # (3 - 1) = 10 points achieved
                    'id': int,
                    'points_achieved': 10,
                    'step_results': list,
                    '__allow_extra__': True,
                }
            )
            # Nothing should be skipped, so all steps added
            len(res['step_results']) == 4 * 2 * 2
            test_client.req(
                'get',
                f'/api/v1/submissions/{work2["id"]}',
                200,
                result={
                    '__allow_extra__': True,
                    'grade': 10.0,
                }
            )

            # Now you should not be able to see step details anymore
            for step in m.AutoTestStepBase.query:
                step.hidden = True
            session.commit()
            old_step_results = res['step_results']
            res = test_client.req(
                'get', f'{url}/runs/{run.id}/results/{res2}', 200
            )
            for step_res1, step_res2 in zip(
                res['step_results'], old_step_results
            ):
                assert step_res1['id'] == step_res2['id']

                assert step_res1['auto_test_step']['hidden']
                assert not step_res2['auto_test_step']['hidden']

                if step_res1['achieved_points']:
                    assert step_res1['log'] != step_res2['log']
                else:
                    assert step_res1['log'] == {}

    with describe('delete result'):
        with logged_in(student1):
            test_client.req('delete', f'{url}/runs/{run.id}', 403)
        with logged_in(teacher):
            test_client.req('delete', f'{url}/runs/{run.id}', 204)
            test_client.req('get', f'{url}/runs/{run.id}', 404)
            test_client.req(
                'get',
                f'/api/v1/submissions/{work2["id"]}',
                200,
                result={
                    '__allow_extra__': True,
                    'grade': None,
                }
            )


def test_update_auto_test_set(basic, test_client, logged_in, describe):
    test = set_id = suite_url = suite = url = None

    def update_test():
        with logged_in(teacher):
            nonlocal test, set_id, suite, suite_url, url
            old_test = test
            test = test_client.req('get', url, 200)
            assert test['id'] == old_test['id']

            set_id = test['sets'][0]['id']
            assert old_test['sets'][0]['id'] == set_id

            suite = test['sets'][0]['suites'][0]
            suite_url = f'{url}/sets/{set_id}/suites/'

    def update_suite(**new_data):
        test_client.req(
            'patch',
            suite_url,
            new_data.pop('error', 200),
            data={
                **suite,
                'rubric_row_id': suite['rubric_row']['id'],
                **new_data,
            }
        )
        update_test()

    def update_set(**new_data):
        test_client.req(
            'patch',
            f'{url}/sets/{set_id}',
            new_data.pop('error', 200),
            data={
                **test['sets'][0],
                **new_data,
            }
        )
        update_test()

    with describe('setup'):
        course, assig_id, teacher, student = basic
        with logged_in(teacher):
            test = helpers.create_auto_test(test_client, assig_id)
            url = f'/api/v1/auto_tests/{test["id"]}'
            update_test()

    with describe('update stop points'), logged_in(teacher):
        update_set(stop_points=-1, error=400)
        update_set(stop_points=23, error=400)
        update_set(stop_points=0.5)
        assert test['sets'][0]['stop_points'] == 0.5

    with describe('Set internet can be enabled and disabled'
                  ), logged_in(teacher):
        update_suite(network_disabled=False)
        assert suite['network_disabled'] is False

        update_suite(network_disabled=True)
        assert suite['network_disabled'] is True

    with describe('Remove steps'), logged_in(teacher):
        assert suite['steps']
        update_suite(steps=[])
        assert suite['steps'] == []

    with describe('Add new step'), logged_in(teacher):
        update_suite(steps=[helpers.get_auto_test_run_program_step()])
        assert suite['steps'][0]['type'] == 'run_program'
        assert isinstance(suite['steps'][0]['id'], int)

    with describe('Unknown step types result in a 404'), logged_in(teacher):
        old_steps = suite['steps']
        update_suite(
            steps=[{**helpers.get_auto_test_io_step(), 'type': 'UNKOWN'}],
            error=400,
        )
        assert suite['steps'] == old_steps

    with describe('Cannot change the type of a step'), logged_in(teacher):
        old_steps = suite['steps']
        update_suite(steps=[{**old_steps[0], 'type': 'io_test'}], error=404)
        assert suite['steps'] == old_steps

    with describe('Cannot set the time limit to < 1'), logged_in(teacher):
        update_suite(command_time_limit=2, error=200)
        assert suite['command_time_limit'] == 2
        update_suite(command_time_limit=0.5, error=400)
        assert suite['command_time_limit'] == 2
        update_suite(command_time_limit=-1, error=400)
        assert suite['command_time_limit'] == 2
        update_suite(command_time_limit=20, error=200)
        assert suite['command_time_limit'] == 20

    with describe('delete suite'), logged_in(teacher):
        test_client.req('delete', f'{suite_url}{suite["id"]}', 204)
        test_client.req(
            'get',
            url,
            200,
            result={
                'sets': [{'__allow_extra__': True, 'suites': []}],
                '__allow_extra__': True,
            }
        )

    with describe('delete set'), logged_in(teacher):
        test_client.req('delete', f'{url}/sets/{set_id}', 204)
        test_client.req(
            'get', url, 200, result={'sets': [], '__allow_extra__': True}
        )


def test_internal_api_auth(test_client, app, describe, session):
    with describe('setup'):
        ipaddr = object()
        other_ipaddr = object()
        run = m.AutoTestRun()
        runner = m.AutoTestRunner(_ipaddr=ipaddr, run=run, id=uuid.uuid4())
        assert runner.id

        verify_runner = psef.v_internal.auto_tests._verify_and_get_runner

    with describe('Without correct global password'):
        test_client.req(
            'get',
            '/api/v-internal/auto_tests/',
            401,
            headers={'CG-Internal-Api-Password': 'INVALID!'}
        )

    with describe('no runner to verify_runner'):
        with pytest.raises(psef.exceptions.PermissionException):
            verify_runner(None, ('', False))

    with describe('wrong password to any verify_runner'):
        with pytest.raises(psef.exceptions.PermissionException):
            verify_runner(run, ('', False))

        with pytest.raises(psef.exceptions.PermissionException):
            verify_runner(run, ('Not correct', False))

    with app.test_request_context(
        '/', environ_base={'REMOTE_ADDR': other_ipaddr}
    ):
        with describe('Wrong ip address'):
            with pytest.raises(psef.exceptions.PermissionException):
                verify_runner(run, (str(runner.id), True))

            # It should work when verification is turned off
            assert runner == verify_runner(run, (str(runner.id), False))

            runner._ipaddr = other_ipaddr

            # It should work when ip is correct
            assert runner == verify_runner(run, (str(runner.id), True))

        with describe('no run should not work'):
            runner.run = None
            with pytest.raises(psef.exceptions.PermissionException):
                verify_runner(run, (str(runner.id), True))


def test_update_locked_rubric(
    session, basic, test_client, logged_in, describe, app
):
    with describe('setup'):
        course, assig_id, teacher, student = basic
        rubric_data = helpers.get_simple_rubric()
        with logged_in(teacher):
            rubric = test_client.req(
                'put',
                f'/api/v1/assignments/{assig_id}/rubrics/',
                200,
                data=rubric_data
            )
            items = [
                row.items[0].id
                for row in m.RubricRow.query.filter_by(assignment_id=assig_id)
            ]

            test_client.req(
                'patch',
                f'/api/v1/assignments/{assig_id}',
                200,
                data={'state': 'open'}
            )

        with logged_in(student):
            work = helpers.create_submission(test_client, assig_id)

    with describe('can update non locked rubric rows'):
        with logged_in(teacher):
            test_client.req(
                'patch',
                f'/api/v1/submissions/{work["id"]}/rubricitems/',
                204,
                data={'items': items}
            )

    with describe('cannot update locked rubric rows'):
        with logged_in(teacher):
            test_id = helpers.create_auto_test(
                test_client, assig_id, 0, 0, grade_calculation='full'
            )['id']
            set_id = test_client.req(
                'post', f'/api/v1/auto_tests/{test_id}/sets/', 200
            )['id']
            _, res = test_client.req(
                'patch',
                f'/api/v1/auto_tests/{test_id}/sets/{set_id}/suites/',
                200,
                data={
                    'steps': [helpers.get_auto_test_io_step()],
                    'rubric_row_id': rubric[0]['id'],
                    'network_disabled': True,
                },
                include_response=True,
            )
            assert 'Warning' in res.headers

            # This does not fail as we post the same item
            test_client.req(
                'patch',
                f'/api/v1/submissions/{work["id"]}/rubricitems/',
                204,
                data={'items': items}
            )

            items = [
                row.items[1].id
                for row in m.RubricRow.query.filter_by(assignment_id=assig_id)
            ]
            # This does not work as the item has changed
            test_client.req(
                'patch',
                f'/api/v1/submissions/{work["id"]}/rubricitems/',
                400,
                data={'items': items}
            )

    with describe('cannot delete locked rubric rows'), logged_in(teacher):
        res = test_client.req(
            'put',
            f'/api/v1/assignments/{assig_id}/rubrics/',
            400,
            data={'rows': []}
        )
        assert 'cannot delete a locked' in res['message']

    with describe('cannot delete a rubric with locked rows'
                  ), logged_in(teacher):
        res = test_client.req(
            'delete',
            f'/api/v1/assignments/{assig_id}/rubrics/',
            409,
        )
        assert 'cannot delete a rubric with locked' in res['message']

    with describe('cannot delete items from locked rubric row after run'
                  ), logged_in(teacher):
        print(rubric)
        rubric_data = {'rows': rubric}
        old_rubric_data = copy.deepcopy(rubric_data)
        rubric_data['rows'][0]['items'].pop()
        # Before should work
        rubric = test_client.req(
            'put',
            f'/api/v1/assignments/{assig_id}/rubrics/',
            200,
            data=rubric_data
        )
        with app.test_request_context('/non_existing', {}):
            assig = m.Assignment.query.get(assig_id)
            assig.auto_test.start_test_run()
            session.commit()
        err = test_client.req(
            'put',
            f'/api/v1/assignments/{assig_id}/rubrics/',
            400,
            data=old_rubric_data
        )
        assert 'No items can be added or deleted' in err['message']


def test_hidden_steps(describe, test_client, logged_in, session, basic):
    with describe('setup'):
        course, assig_id, teacher, student = basic
        with logged_in(teacher):
            test = helpers.create_auto_test(test_client, assig_id)
            for step in m.AutoTestStepBase.query:
                step.hidden = True
            session.commit()

            test_client.req(
                'patch',
                f'/api/v1/assignments/{assig_id}',
                200,
                data={'state': 'done'}
            )

        url = f'/api/v1/auto_tests/{test["id"]}'

    with describe('student cannot see hidden test'):
        with logged_in(student):
            step = {
                'id': int,
                'name': str,
                'type': str,
                'weight': float,
                'hidden': True,
                'data': {'?inputs?': list},
            }
            test_client.req(
                'get',
                url,
                200,
                result={
                    '__allow_extra__': True,
                    'sets': [{
                        '__allow_extra__': True,
                        'suites': [{
                            '__allow_extra__': True, 'steps': [step] * 4
                        }],
                    }],
                }
            )


def test_get_runs_internal_api(
    test_client, describe, app, session, basic, logged_in
):
    with describe('Get runs without password'):
        test_client.req('get', '/api/v-internal/auto_tests/', 400)

    with describe('Get runs when there are no runs'):
        test_client.req(
            'get',
            '/api/v-internal/auto_tests/?get=tests_to_run',
            204,
            headers={
                'CG-Internal-Api-Password': app.config['AUTO_TEST_PASSWORD']
            }
        )

    with describe('setup'):
        run = m.AutoTestRun(started_date=None, auto_test=m.AutoTest())
        session.add(run)
        course, assig_id, teacher, student = basic

        with logged_in(teacher):
            test = helpers.create_auto_test(test_client, assig_id)
        run = m.AutoTestRun(
            started_date=None,
            auto_test_id=test['id'],
            is_continuous_feedback_run=True
        )
        session.commit()

    with describe('With runs but with failing broker'):
        test_client.req(
            'get',
            '/api/v-internal/auto_tests/?get=tests_to_run',
            204,
            headers={
                'CG-Internal-Api-Password': app.config['AUTO_TEST_PASSWORD']
            }
        )


@pytest.mark.parametrize('use_transaction', [False], indirect=True)
def test_continuous_feedback_auto_test(
    monkeypatch_celery, monkeypatch_broker, basic, test_client, logged_in,
    describe, live_server, lxc_stub, monkeypatch, app, session,
    stub_function_class, assert_similar, monkeypatch_for_run
):
    tmpdir = None

    with describe('setup'):
        course, assig_id, teacher, student = basic

        with logged_in(teacher):
            test = helpers.create_auto_test(
                test_client,
                assig_id,
                amount_sets=2,
                amount_suites=2,
                amount_fixtures=1,
                stop_points=[0.5, None],
                grade_calculation='partial',
            )
            test_client.req(
                'patch',
                f'/api/v1/assignments/{assig_id}',
                200,
                data={'state': 'open'}
            )

        url = f'/api/v1/auto_tests/{test["id"]}'
        live_server()

        with logged_in(student):
            prog = """
            ls
            """
            helpers.create_submission(
                test_client,
                assig_id,
                submission_data=(io.BytesIO(dedent(prog).encode()), 'test.py')
            )

        _run_student = psef.auto_test._run_student

        monkeypatch.setattr(
            psef.auto_test, '_get_home_dir',
            stub_function_class(lambda: tmpdir)
        )

        def next_student(*args, **kwargs):
            nonlocal tmpdir

            with tempfile.TemporaryDirectory() as tdir:
                tmpdir = tdir
                for inner in ['/student', '/fixtures']:
                    shutil.copytree(upper_tmpdir + inner, tdir + inner)
                return _run_student(*args, **kwargs)

        monkeypatch.setattr(psef.auto_test, '_run_student', next_student)

    with describe('start_auto_test'
                  ), tempfile.TemporaryDirectory() as upper_tmpdir:
        tmpdir = upper_tmpdir

        t = m.AutoTest.query.get(test['id'])
        psef.auto_test.CODEGRADE_USER = getpass.getuser()
        session.commit()

        with logged_in(teacher):
            test_client.req(
                'post',
                f'{url}/runs/',
                200,
                data={
                    'continuous_feedback_run': True,
                }
            )
            session.commit()

        run = t.continuous_feedback_run
        assert run is not None

        # Old submission should not be started directly
        assert session.query(m.AutoTestResult).all() == []

        with logged_in(student):
            prog = """
            import sys
            if len(sys.argv) > 1:
                print("hello {}!".format(sys.argv[1]))
            else:
                print("hello stranger!")
            """
            work = helpers.create_submission(
                test_client,
                assig_id,
                submission_data=(io.BytesIO(dedent(prog).encode()), 'test.py')
            )

        assert len(session.query(m.AutoTestResult).all()) == 1
        res = session.query(m.AutoTestResult).one()

        with logged_in(student):
            # A student can see results before the assignment is done
            test_client.req(
                'get',
                f'{url}/runs/{run.id}/results/{res.id}',
                200,
                result={
                    'state': 'not_started',
                    'approx_waiting_before': 0,
                    '__allow_extra__': True,
                }
            )

        psef.auto_test.start_polling(app.config, repeat=False)

        with logged_in(student):
            # A student can see results before the assignment is done
            test_client.req(
                'get',
                f'{url}/runs/{run.id}/results/{res.id}',
                200,
                result={
                    'state': 'passed',
                    'approx_waiting_before': None,
                    '__allow_extra__': True,
                }
            )

        with logged_in(teacher):
            # Make sure rubric is not filled in
            test_client.req(
                'get',
                f'/api/v1/submissions/{work["id"]}',
                200,
                result={
                    '__allow_extra__': True,
                    'grade': None,
                    'grade_overridden': False,
                }
            )

        with pytest.raises(APIException):
            t.start_continuous_feedback_run()


def test_getting_fixture_no_permission(
    describe, basic, logged_in, test_client, session, app
):
    with describe('setup'):
        course, assig_id, teacher, student = basic
        with logged_in(teacher):
            test = helpers.create_auto_test(
                test_client,
                assig_id,
                amount_sets=2,
                amount_suites=2,
                amount_fixtures=1,
                stop_points=[0.5, None],
                grade_calculation='partial',
            )

            session.commit()

    fixture = m.AutoTestFixture.query.first()
    test_client.req(
        'get',
        '/api/v-internal/auto_tests/{}/fixtures/{}'.format(
            fixture.auto_test_id, fixture.id
        ),
        403,
        headers={'CG-Internal-Api-Password': app.config['AUTO_TEST_PASSWORD']}
    )


def test_run_command_too_much_output(
    describe, monkeypatch_for_run, app, monkeypatch, stub_function_class
):
    monkeypatch.setitem(app.config, 'AUTO_TEST_MAX_OUTPUT_TAIL', 64)
    monkeypatch.setitem(app.config, 'AUTO_TEST_OUTPUT_LIMIT', 128)
    cmd = 'echo -n "' + 'a' * 128 + 'b' * 128 + 'c' * 32 + '"'
    with tempfile.TemporaryDirectory(
    ) as tmpdir, psef.auto_test._get_base_container(
        app.config
    ).started_container() as cont:
        os.mkdir(os.path.join(tmpdir, 'student'))

        monkeypatch.setattr(
            psef.auto_test, '_get_home_dir',
            stub_function_class(lambda: tmpdir)
        )
        with describe('without capturing extra output'):
            res = cont.run_student_command(cmd, 6)
            assert res.exit_code == 0
            assert res.stdout == 'a' * 128 + ' <OUTPUT TRUNCATED>\n'
            assert res.stderr == ''
            assert list(res.stdout_tail.data) == []

        with describe('with capturing extra output'):
            res = cont.run_student_command(cmd, 6, keep_stdout_tail=True)
            assert res.exit_code == 0
            assert res.stdout == 'a' * 128 + ' <OUTPUT TRUNCATED>\n'
            assert res.stderr == ''
            assert bytes(res.stdout_tail.data
                         ).decode() == ('b' * 32 + 'c' * 32)


@pytest.mark.parametrize(
    'filename', ['../test_submissions/single_dir_archive.zip'], indirect=True
)
def test_ensure_from_latest_work(session, describe, assignment_real_works):
    with describe('setup'):
        assignment, submission = assignment_real_works
        sub2_id = m.Work.query.filter_by(assignment_id=assignment.id).filter(
            m.Work.id != submission['id']
        ).first().id
        new_work = m.Work(
            user_id=submission['user']['id'], assignment_id=assignment.id
        )
        session.add(new_work)
        session.commit()

        test = m.AutoTest(
            setup_script='', run_setup_script='', assignment=assignment
        )
        run = m.AutoTestRun(
            _job_id=uuid.uuid4(),
            auto_test=test,
            is_continuous_feedback_run=True,
        )
        oldest = m.AutoTestResult(work_id=submission['id'])
        latest2 = m.AutoTestResult(work_id=sub2_id)
        run.results = [latest2, oldest]
        session.commit()
        latest = m.AutoTestResult(work_id=new_work.id)
        run.results.append(latest)
        session.commit()

    with describe('should work with latest'):
        psef.v_internal.auto_tests._ensure_from_latest_work(latest)
        psef.v_internal.auto_tests._ensure_from_latest_work(latest2)

    with describe('should raise for non latest submission'):
        with pytest.raises(APIException) as err:
            psef.v_internal.auto_tests._ensure_from_latest_work(oldest)
        assert err.value.api_code == APICodes.NOT_NEWEST_SUBMSSION
