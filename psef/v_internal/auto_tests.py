"""This module implements the internal API for AutoTest runs.

All these routes need authentication, and can only be requested by ip addresses
which are registered as active runners.

SPDX-License-Identifier: AGPL-3.0-only
"""
import typing as t

import requests
import werkzeug
import structlog
from flask import g, request, make_response, send_from_directory

from . import api
from .. import app, files, models, helpers, auto_test
from ..models import db
from ..helpers import (
    JSONResponse, EmptyResponse, jsonify, get_or_404, make_empty_response,
    filter_single_or_404, get_from_map_transaction, get_json_dict_from_request
)
from ..parsers import parse_enum
from ..features import Feature, feature_required
from ..exceptions import APICodes, PermissionException

logger = structlog.get_logger()
LocalRunner = t.NewType('LocalRunner', t.Tuple[str, bool])


def _get_local_runner(
    global_password: str, local_password: str
) -> LocalRunner:
    if global_password != app.config['AUTO_TEST_PASSWORD']:
        raise PermissionException(
            'You do not have permission to use this route',
            'No valid password given', APICodes.NOT_LOGGED_IN, 401
        )

    return LocalRunner(
        (local_password, not app.config['AUTO_TEST_DISABLE_ORIGIN_CHECK'])
    )


def _verify_runner(
    runner: t.Optional[models.AutoTestRunner], local: LocalRunner
) -> None:
    password, check_ip = local
    exc = PermissionException(
        'You do not have permission to use this route',
        'No valid password given', APICodes.NOT_LOGGED_IN, 401
    )

    if runner is None:
        raise exc
    elif not password or not runner.id or password != str(runner.id):
        raise exc
    elif check_ip and runner.ipaddr != request.remote_addr:
        raise exc

    if runner.run is None or runner.run.finished:
        raise PermissionException(
            'You cannot update runs which have finished',
            f'The run {{ runner.run_id }} has finished',
            APICodes.INCORRECT_PERMISSION, 403
        )


def _verify_global_header_password() -> LocalRunner:
    with get_from_map_transaction(request.headers) as [get, opt_get]:
        global_password = get('CG-Internal-Api-Password', str)
        local_password = opt_get('CG-Internal-Api-Runner-Password', str, '')
    return _get_local_runner(global_password, local_password)


@api.route('/auto_tests/', methods=['GET'])
@feature_required(Feature.AUTO_TEST)
def get_auto_test_status(
) -> t.Union[JSONResponse[auto_test.RunnerInstructions], EmptyResponse]:
    """Request a AutoTest to run.

    .. warning:: This route has side effects!

    This route only does something when the get parameter ``get`` is equal to
    ``tests_to_run``. This route may also be slow as it asks the broker if the
    requesting runner is allowed to be used.
    """
    _verify_global_header_password()
    to_get = request.args.get('get', object())

    if to_get == 'tests_to_run':
        runs = models.AutoTestRun.query.filter_by(
            started_date=None,
        ).with_for_update()

        with helpers.BrokerSession() as ses:
            for run in runs:
                logger.info(
                    'Trying to register job for runner',
                    run=run.__to_json__(),
                    job_id=run.get_job_id(),
                    runner_ip=request.remote_addr,
                )

                try:
                    ses.post(
                        f'/api/v1/jobs/{run.get_job_id()}/runners/',
                        json={
                            'runner_ip': request.remote_addr
                        }
                    ).raise_for_status()
                except requests.RequestException:
                    logger.info(
                        'Run cannot be done by given runner',
                        exc_info=True,
                        run_id=run.id,
                    )
                else:
                    run.start(request.remote_addr)
                    db.session.commit()
                    return jsonify(run.get_instructions())

    return make_empty_response()


@api.route(
    '/auto_tests/<int:auto_test_id>/runs/<int:run_id>', methods=['PATCH']
)
@feature_required(Feature.AUTO_TEST)
def update_run(auto_test_id: int, run_id: int) -> EmptyResponse:
    """Update the state of the given run.

    :>json state: The new state of the run (OPTIONAL).
    :>json setup_stdout: The stdout of the run (so the one which is executed
        only once during the run) setup script (OPTIONAL).
    :>json setup_stderr: Same as ``setup_stdout`` but for the stderr
        (OPTIONAL).
    """
    password = _verify_global_header_password()

    with get_from_map_transaction(get_json_dict_from_request()) as [_, opt]:
        state = opt('state', str, None)
        setup_stdout = opt('setup_stdout', str, None)
        setup_stderr = opt('setup_stderr', str, None)

    run = filter_single_or_404(
        models.AutoTestRun,
        models.AutoTestRun.id == run_id,
        models.AutoTest.id == auto_test_id,
    )
    _verify_runner(run.runner, password)

    if state is not None:
        new_state = parse_enum(state, models.AutoTestRunState)
        assert new_state is not None
        run.state = new_state
    if setup_stdout is not None:
        run.setup_stdout = setup_stdout
    if setup_stderr is not None:
        run.setup_stderr = setup_stderr

    db.session.commit()

    return make_empty_response()


@api.route(
    '/auto_tests/<int:auto_test_id>/results/<int:result_id>', methods=['GET']
)
@feature_required(Feature.AUTO_TEST)
def get_result_data(auto_test_id: int, result_id: int
                    ) -> t.Union[werkzeug.wrappers.Response, EmptyResponse]:
    """Get the submission files for the given result_id.

    The files are zipped and this zip is send. This zip DOES NOT contain a top
    level directory.
    """
    password = _verify_global_header_password()

    result = get_or_404(
        models.AutoTestResult,
        result_id,
        also_error=lambda res: res.run.auto_test_id != auto_test_id,
    )

    runner = result.run.runner
    _verify_runner(runner, password)

    res = make_empty_response()

    if request.args.get('type', None) == 'submission_files':
        file_name = result.work.create_zip(
            models.FileOwner.teacher,
            create_leading_directory=False,
        )
        directory = app.config['MIRROR_UPLOAD_DIR']
        res = send_from_directory(directory, file_name)

    return res


@api.route(
    '/auto_tests/<int:auto_test_id>/runs/<int:run_id>/heartbeats/',
    methods=['POST']
)
def post_heartbeat(auto_test_id: int, run_id: int) -> EmptyResponse:
    """Emit a heartbeat for the given AutoTest run.

    :param auto_test_id: The AutoTest where the given run is in.
    :param run_id: The id of the run for which you want to emit a heartbeat.
    """
    password = _verify_global_header_password()

    run = filter_single_or_404(
        models.AutoTestRun,
        models.AutoTestRun.id == run_id,
        models.AutoTest.id == auto_test_id,
    )
    _verify_runner(run.runner, password)
    assert run.runner is not None

    run.runner.last_heartbeat = g.request_start_time
    db.session.commit()
    return make_empty_response()


@api.route(
    '/auto_tests/<int:auto_test_id>/runs/<int:run_id>/logs/', methods=['POST']
)
@feature_required(Feature.AUTO_TEST)
def emit_log_for_runner(auto_test_id: int, run_id: int) -> EmptyResponse:
    """Emit log lines for the current runner.
    """
    password = _verify_global_header_password()

    with get_from_map_transaction(
        get_json_dict_from_request(log_object=False)
    ) as [get, _]:
        logs = get('logs', list)

    run = filter_single_or_404(
        models.AutoTestRun,
        models.AutoTestRun.id == run_id,
        models.AutoTest.id == auto_test_id,
    )
    _verify_runner(run.runner, password)

    for log in logs:
        assert isinstance(log, dict)
        assert 'level' in log
        getattr(logger, log['level'], logger.info)(
            **log,
            from_tester=True,
            original_timestamp=log['timestamp'],
            run_id=run_id
        )

    return make_empty_response()


@api.route(
    '/auto_tests/<int:auto_test_id>/fixtures/<int:fixture_id>',
    methods=['GET']
)
@feature_required(Feature.AUTO_TEST)
def get_fixture(
    auto_test_id: int, fixture_id: int
) -> werkzeug.wrappers.Response:
    """Get the contents of the given fixture.

    :param auto_test_id: The id of the AutoTest where this fixture is in.
    :param fixture_id: The id of the fixture to get.
    """
    password = _verify_global_header_password()

    fixture = get_or_404(
        models.AutoTestFixture,
        fixture_id,
        also_error=lambda obj: obj.auto_test_id != auto_test_id,
    )

    runs = fixture.auto_test.runs
    runner = runs[0].runner if runs else None
    _verify_runner(runner, password)

    contents = files.get_file_contents(fixture)
    res: werkzeug.wrappers.Response = make_response(contents)
    res.headers['Content-Type'] = 'application/octet-stream'
    return res


@api.route(
    '/auto_tests/<int:auto_test_id>/results/<int:result_id>',
    methods=['PATCH']
)
@feature_required(Feature.AUTO_TEST)
def update_result(auto_test_id: int, result_id: int) -> EmptyResponse:
    """Update the the state of a result.

    This route does not update the results of steps!

    :param auto_test_id: The AutoTest configuration in which to update the
        result.
    :param result_id: The id of the result which you want to update.
    :>json state: The new state of the result (OPTIONAL).
    :>json setup_stdout: The output of the setup script (OPTIONAL).
    :>json setup_stderr: The outuput to stderr of the setup script (OPTIONAL).
    """
    password = _verify_global_header_password()

    with get_from_map_transaction(get_json_dict_from_request()) as [
        _, opt_get
    ]:
        state = opt_get('state', str, None)
        setup_stdout = opt_get('setup_stdout', str, None)
        setup_stderr = opt_get('setup_stderr', str, None)

    result = filter_single_or_404(
        models.AutoTestResult,
        models.AutoTestResult.id == result_id,
        models.AutoTest.id == auto_test_id,
    )
    _verify_runner(result.run.runner, password)

    if state is not None:
        new_state = parse_enum(state, models.AutoTestStepResultState)
        assert new_state is not None
        result.state = new_state
    if setup_stdout is not None:
        result.setup_stdout = setup_stdout
    if setup_stderr is not None:
        result.setup_stderr = setup_stderr

    db.session.commit()
    return make_empty_response()


@api.route(
    '/auto_tests/<int:auto_test_id>/results/<int:result_id>/step_results/',
    methods=['PUT']
)
@feature_required(Feature.AUTO_TEST)
def update_step_result(auto_test_id: int, result_id: int
                       ) -> JSONResponse[models.AutoTestStepResult]:
    """Update the result of a single step.

    :param auto_test_id: The AutoTest configuration in which to update the
        result.
    :param result_id: The id of the result in which to update the step.
    :>json state: The state in which the step is in right now.
    :>json log: The current log of the step.
    :>json auto_test_step_id: The step of which this is a result.
    :>json res_id: The step result you want to update (OPTIONAL). If you do not
        pass this option a step result is created.
    """
    password = _verify_global_header_password()

    with get_from_map_transaction(get_json_dict_from_request()) as [
        get, opt_get
    ]:
        state = get('state', str)
        log = get('log', dict)
        auto_test_step_id = get('auto_test_step_id', int)
        res_id = opt_get('id', int, None)

    result = get_or_404(
        models.AutoTestResult,
        result_id,
        also_error=lambda res: res.run.auto_test_id != auto_test_id,
    )
    _verify_runner(result.run.runner, password)

    if res_id is None:
        step_result = models.AutoTestStepResult(
            step=get_or_404(  # type: ignore
                models.AutoTestStepBase,
                auto_test_step_id
            ),
            result=result
        )
        db.session.add(result)
    else:
        step_result = filter_single_or_404(
            models.AutoTestStepResult,
            models.AutoTestStepResult.id == res_id,
            models.AutoTestStepResult.auto_test_result_id == result.id,
            models.AutoTestStepResult.auto_test_step_id == auto_test_step_id,
        )

    new_state = parse_enum(state, models.AutoTestStepResultState)
    assert new_state is not None
    step_result.state = new_state

    step_result.log = log

    db.session.commit()

    return jsonify(step_result)
