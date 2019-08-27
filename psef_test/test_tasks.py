import time
import uuid
from datetime import datetime

import pytest

from psef import tasks as t
from psef import models as m


@pytest.mark.parametrize(
    'filename', ['../test_submissions/single_dir_archive.zip'], indirect=True
)
def test_check_heartbeat(
    session, describe, monkeypatch, stub_function_class, app,
    assignment_real_works, monkeypatch_celery
):
    assignment, submission = assignment_real_works

    with describe('setup'):
        stub_heart = stub_function_class()
        monkeypatch.setattr(t, 'check_heartbeat_auto_test_run', stub_heart)

        stub_notify_new = stub_function_class()
        monkeypatch.setattr(t, '_notify_broker_of_new_job_1', stub_notify_new)

        stub_notify_stop = stub_function_class()
        monkeypatch.setattr(t, 'notify_broker_end_of_job', stub_notify_stop)

        test = m.AutoTest(
            setup_script='', run_setup_script='', assignment=assignment
        )
        run = m.AutoTestRun(_job_id=uuid.uuid4(), auto_test=test)
        run.results = [
            m.AutoTestResult(work_id=submission['id']),
            m.AutoTestResult(work_id=submission['id'])
        ]
        run.results[0].state = m.AutoTestStepResultState.failed
        run.results[1].state = m.AutoTestStepResultState.passed
        session.add(run)

        with app.test_request_context('/non_existing', {}):
            run.add_active_runner('localhost')
        runner = run.runners[0]
        assert runner.run
        session.commit()

    with describe('not expired'):
        t._check_heartbeat_stop_test_runner_1(runner.id.hex)
        now = datetime.utcnow()

        # As the heartbeats have not expired yet a new check should be
        # scheduled
        assert len(stub_heart.all_args) == 1
        assert stub_heart.all_args[0][0] == (runner.id.hex, )
        assert (stub_heart.all_args[0]['eta'] - now).total_seconds() > 0

        assert not stub_notify_new.called
        assert not stub_notify_stop.all_args

    with describe('Already finished'):
        with describe('Inner setup'):
            # Use _state as the setter does logic we don't wan't right now
            run._state = m.AutoTestRunState.done
        session.commit()
        t._check_heartbeat_stop_test_runner_1(runner.id.hex)

        assert not stub_heart.called
        assert not stub_notify_new.called
        assert not stub_notify_stop.called

        run._state = m.AutoTestRunState.running
        session.commit()

    with describe('expired'):
        runner.last_heartbeat = datetime.fromtimestamp(0)
        old_job_id = run.get_job_id()
        session.commit()
        run = runner.run
        t._check_heartbeat_stop_test_runner_1(runner.id.hex)

        assert not stub_heart.called
        assert len(stub_notify_new.all_args) == 1
        assert len(stub_notify_stop.all_args) == 1
        assert stub_notify_new.call_dates[0] > stub_notify_stop.call_dates[0]

        run.get_job_id() != old_job_id
        assert runner.run is None
        assert run.state == m.AutoTestRunState.running
        assert (
            run.results[0].state == m.AutoTestStepResultState.not_started
        ), 'The results should be cleared'
        assert (
            run.results[1].state == m.AutoTestStepResultState.passed
        ), 'Passed results should not be cleared'

    with describe('With non existing runner'):
        t._check_heartbeat_stop_test_runner_1(uuid.uuid4().hex)

        assert not stub_heart.called
        assert not stub_notify_new.called
        assert not stub_notify_stop.called


def test_stop_auto_test_run(
    session, describe, monkeypatch, stub_function_class, app,
    monkeypatch_celery
):
    with describe('setup'):
        stub_stop = stub_function_class()
        monkeypatch.setattr(t, 'stop_auto_test_run', stub_stop)

        stub_notify_stop = stub_function_class()
        monkeypatch.setattr(t, 'notify_broker_end_of_job', stub_notify_stop)

        test = m.AutoTest(setup_script='', run_setup_script='')
        run = m.AutoTestRun(_job_id=uuid.uuid4(), auto_test=test)
        run.state = m.AutoTestRunState.running
        session.add(run)

        with app.test_request_context('/non_existing', {}):
            run.add_active_runner('localhost')
        session.commit()

    with describe('kill before deadline'):
        t._stop_auto_test_run_1(run.id)

        assert len(stub_stop.all_args) == 1
        assert stub_stop.all_args[0][0] == (run.id, )
        assert stub_stop.all_args[0]['eta'] == run.kill_date

        assert not stub_notify_stop.called

    with describe('kill after deadline'):
        run.kill_date = datetime.utcnow()
        old_job_id = run.get_job_id()
        session.commit()

        t._stop_auto_test_run_1(run.id)

        assert not stub_stop.called

        assert len(stub_notify_stop.all_args) == 1
        assert stub_notify_stop.all_args[0][0] == old_job_id
        assert run.state == m.AutoTestRunState.timed_out

    with describe('kill after already done'):
        t._stop_auto_test_run_1(run.id)

        assert not stub_stop.called
        assert not stub_notify_stop.called

    with describe('kill with unknown runner'):
        t._stop_auto_test_run_1((run.id + 2) ** 4)

        assert not stub_stop.called
        assert not stub_notify_stop.called
