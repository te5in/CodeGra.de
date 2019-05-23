import typing as t
import datetime

import werkzeug
import structlog
from flask import g, request, make_response, send_from_directory

from . import api
from .. import app, files, models, auto_test
from ..models import db
from ..helpers import (
    JSONResponse, EmptyResponse, jsonify, get_or_404, request_arg_true,
    make_empty_response, filter_single_or_404, get_from_map_transaction,
    get_json_dict_from_request
)
from ..parsers import parse_enum
from ..features import Feature, feature_required
from ..exceptions import APICodes, APIException, PermissionException

logger = structlog.get_logger()
LocalRunner = t.NewType('LocalRunner', t.Tuple[str, bool])


def get_local_runner(global_password: str, local_password: str) -> LocalRunner:
    config_dict = app.config['AUTO_TEST_CREDENTIALS'].get(
        request.remote_addr, None
    )
    if config_dict is None and global_password in {
        v['password']
        for v in app.config['AUTO_TEST_CREDENTIALS'].values()
        if v.get('disable_origin_check', False)
    }:
        return LocalRunner((local_password, False))

    stored_password = config_dict and config_dict['password']

    if not global_password or global_password != stored_password:
        raise PermissionException(
            'You do not have permission to use this route',
            'No valid password given', APICodes.NOT_LOGGED_IN, 401
        )

    return LocalRunner((local_password, True))


def verify_runner(
    runner: t.Optional[models.AutoTestRunner], local: LocalRunner
) -> None:
    password, check_ip = local

    if (
        runner is None or not password or str(runner.id) != password or
        runner.after_state != models.AutoTestAfterRunState.not_called or
        (check_ip and runner.ipaddr != request.remote_addr)
    ):
        raise PermissionException(
            'You do not have permission to use this route',
            'No valid password given', APICodes.NOT_LOGGED_IN, 401
        )

    if (
        runner.run is None or
        runner.run.state == models.AutoTestRunState.timed_out
    ):
        raise PermissionException(
            'You cannot update runs which timed out',
            f'The run {{ runner.run.id }} has timed out',
            APICodes.INCORRECT_PERMISSION, 403
        )


def verify_global_header_password() -> LocalRunner:
    with get_from_map_transaction(request.headers) as [get, opt_get]:
        global_password = get('CG-Internal-Api-Password', str)
        local_password = opt_get('CG-Internal-Api-Runner-Password', str, '')
    return get_local_runner(global_password, local_password)


@api.route('/auto_tests/', methods=['GET'])
@feature_required(Feature.AUTO_TEST)
def get_auto_test_status(
) -> t.Union[JSONResponse[auto_test.RunnerInstructions], EmptyResponse]:
    if request.args.get('get', object()) != 'tests_to_run':
        return make_empty_response()

    verify_global_header_password()

    config_dict = app.config['AUTO_TEST_CREDENTIALS'][request.remote_addr]

    if models.AutoTestRunner.already_running(request.remote_addr):
        logger.warning(
            'IP which had already ran tried getting tests',
            remote_addr=request.remote_addr,
        )
        return make_empty_response()

    run = models.AutoTestRun.query.filter_by(
        started_date=None,
    ).with_for_update().first()

    if run is None:
        return make_empty_response()

    run.start(config_dict['type'], request.remote_addr)
    db.session.commit()

    return jsonify(run.get_instructions())


@api.route(
    '/auto_tests/<int:auto_test_id>/runs/<int:run_id>', methods=['PATCH']
)
@feature_required(Feature.AUTO_TEST)
def update_run(auto_test_id: int, run_id: int) -> EmptyResponse:
    password = verify_global_header_password()

    with get_from_map_transaction(get_json_dict_from_request()) as [get, _]:
        state = get('state', str)

    run = filter_single_or_404(
        models.AutoTestRun,
        models.AutoTestRun.id == run_id,
        models.AutoTest.id == auto_test_id,
    )
    verify_runner(run.runner, password)

    new_state = parse_enum(state, models.AutoTestRunState)
    assert new_state is not None
    run.state = new_state
    db.session.commit()

    return make_empty_response()


@api.route(
    '/auto_tests/<int:auto_test_id>/results/<int:result_id>', methods=['GET']
)
@feature_required(Feature.AUTO_TEST)
def get_result_data(auto_test_id: int, result_id: int
                    ) -> t.Union[werkzeug.wrappers.Response, EmptyResponse]:
    password = verify_global_header_password()

    result = get_or_404(
        models.AutoTestResult,
        result_id,
        also_error=lambda res: res.run.auto_test_id != auto_test_id,
    )

    runner = result.run.runner
    verify_runner(runner, password)

    if request.args.get('type', None) == 'submission_files':
        file_name = result.work.create_zip(
            models.FileOwner.teacher,
            create_leading_directory=False,
        )
        directory = app.config['MIRROR_UPLOAD_DIR']
        return send_from_directory(directory, file_name)

    return make_empty_response()


@api.route(
    '/auto_tests/<int:auto_test_id>/runs/<int:run_id>/heartbeats/',
    methods=['POST']
)
def post_heartbeat(auto_test_id: int, run_id: int) -> EmptyResponse:
    password = verify_global_header_password()

    run = filter_single_or_404(
        models.AutoTestRun,
        models.AutoTestRun.id == run_id,
        models.AutoTest.id == auto_test_id,
    )
    verify_runner(run.runner, password)
    assert run.runner is not None

    run.runner.last_heartbeat = g.request_start_time
    db.session.commit()
    return make_empty_response()


@api.route(
    '/auto_tests/<int:auto_test_id>/runs/<int:run_id>/logs/', methods=['POST']
)
@feature_required(Feature.AUTO_TEST)
def emit_log_for_runner(auto_test_id: int, run_id: int) -> EmptyResponse:
    password = verify_global_header_password()

    with get_from_map_transaction(get_json_dict_from_request()) as [get, _]:
        logs = get('logs', list)

    run = filter_single_or_404(
        models.AutoTestRun,
        models.AutoTestRun.id == run_id,
        models.AutoTest.id == auto_test_id,
    )
    verify_runner(run.runner, password)

    for log in logs:
        assert isinstance(log, dict)
        assert 'level' in log
        getattr(logger, log['level'])(
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
    password = verify_global_header_password()

    fixture = filter_single_or_404(
        models.AutoTestFixture,
        models.AutoTestFixture.id == fixture_id,
        models.AutoTest.id == auto_test_id,
    )

    runs = fixture.auto_test.runs
    runner = runs[0].runner if runs else None
    verify_runner(runner, password)

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
    password = verify_global_header_password()

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
    verify_runner(result.run.runner, password)

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
    password = verify_global_header_password()

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
    verify_runner(result.run.runner, password)

    if res_id is None:
        step_result = models.AutoTestStepResult(
            step=get_or_404(models.AutoTestStep, auto_test_step_id),
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
