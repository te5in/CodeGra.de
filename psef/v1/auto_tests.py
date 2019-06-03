import json
import typing as t
import numbers

import werkzeug
import structlog
from flask import request, make_response

from . import api
from .. import app, auth, files, tasks, models, parsers, auto_test, exceptions
from ..models import db
from ..helpers import (
    JSONResponse, EmptyResponse, ExtendedJSONResponse, jsonify, get_or_404,
    add_warning, ensure_json_dict, extended_jsonify, ensure_keys_in_dict,
    make_empty_response, filter_single_or_404, get_files_from_request,
    get_from_map_transaction, get_json_dict_from_request,
    callback_after_this_request
)
from ..features import Feature, feature_required
from ..registry import auto_test_handlers
from ..exceptions import APICodes, APIWarnings, APIException
from ..permissions import CoursePermission as CPerm

logger = structlog.get_logger()


@api.route('/auto_tests/', methods=['POST'])
@feature_required(Feature.AUTO_TEST)
def create_auto_test() -> JSONResponse[models.AutoTest]:
    with get_from_map_transaction(get_json_dict_from_request()) as [get, _]:
        assignment_id = get('assignment_id', int)

    assignment = get_or_404(models.Assignment, assignment_id)
    auth.ensure_permission(CPerm.can_edit_autotest, assignment.course_id)

    auto_test = models.AutoTest(
        assignment=assignment,
        setup_script='',
        run_setup_script='',
        finalize_script='',
    )
    db.session.add(auto_test)
    db.session.commit()
    return jsonify(auto_test)


@api.route('/auto_tests/<int:auto_test_id>', methods=['DELETE'])
@feature_required(Feature.AUTO_TEST)
def delete_auto_test(auto_test_id: int) -> EmptyResponse:
    auto_test = get_or_404(models.AutoTest, auto_test_id)

    auth.ensure_permission(
        CPerm.can_edit_autotest, auto_test.assignment.course_id
    )

    for f in auto_test.fixtures:
        db.session.delete(f)
        callback_after_this_request(f.delete_from_disk)

    db.session.delete(auto_test)
    db.session.commit()

    return make_empty_response()


@api.route(
    '/auto_tests/<int:auto_test_id>/fixtures/<int:fixture_id>',
    methods=['GET']
)
@feature_required(Feature.AUTO_TEST)
def get_fixture_contents(
    auto_test_id: int, fixture_id: int
) -> werkzeug.wrappers.Response:
    fixture = get_or_404(
        models.AutoTestFixture,
        fixture_id,
        also_error=lambda obj: obj.auto_test_id != auto_test_id,
    )

    auth.ensure_can_view_fixture(fixture)

    contents = files.get_file_contents(fixture)
    res: werkzeug.wrappers.Response = make_response(contents)
    res.headers['Content-Type'] = 'application/octet-stream'
    return res


@api.route(
    '/auto_tests/<int:auto_test_id>/fixtures/<int:fixture_id>/hide',
    methods=['POST', 'DELETE']
)
@feature_required(Feature.AUTO_TEST)
def hide_or_open_fixture(auto_test_id: int, fixture_id: int) -> EmptyResponse:
    fixture = filter_single_or_404(
        models.AutoTestFixture,
        models.AutoTest.id == auto_test_id,
        models.AutoTestFixture.id == fixture_id,
    )

    auth.ensure_permission(
        CPerm.can_edit_autotest, fixture.auto_test.assignment.course_id
    )

    fixture.hidden = request.method == 'POST'
    db.session.commit()

    return make_empty_response()


@api.route('/auto_tests/<int:auto_test_id>', methods=['PATCH'])
@feature_required(Feature.AUTO_TEST)
def update_auto_test(auto_test_id: int) -> JSONResponse[models.AutoTest]:
    auto_test = get_or_404(models.AutoTest, auto_test_id)
    auth.ensure_permission(
        CPerm.can_edit_autotest, auto_test.assignment.course_id
    )

    content = ensure_json_dict(
        ('json' in request.files and json.loads(request.files['json'].read()))
        or request.get_json()
    )

    with get_from_map_transaction(content) as [get, optional_get]:
        old_fixtures = optional_get('fixtures', list, None)
        setup_script = optional_get('setup_script', str, None)
        run_setup_script = optional_get('run_setup_script', str, None)
        has_new_fixtures = optional_get('has_new_fixtures', bool, False)

    if old_fixtures is not None:
        old_fixture_set = set(f['id'] for f in old_fixtures)
        for f in auto_test.fixtures:
            if f.id not in old_fixture_set:
                db.session.delete(f)
                callback_after_this_request(f.delete_from_disk)

    if has_new_fixtures:
        new_fixtures = get_files_from_request(
            max_size=app.max_large_file_size,
            keys=['fixture'],
            only_start=True,
        )

        for new_fixture in new_fixtures:
            new_file_name, filename = files.random_file_path()
            new_fixture.save(new_file_name)
            auto_test.fixtures.append(
                models.AutoTestFixture(
                    name=files.escape_logical_filename(new_fixture.filename),
                    filename=filename,
                )
            )
        renames = files.fix_duplicate_filenames(auto_test.fixtures)
        if renames:
            logger.info('Fixtures were renamed', renamed_fixtures=renames)
            add_warning(
                (
                    'Some fixtures were renamed as fixtures with the same name'
                    ' already existed'
                ), APIWarnings.RENAMED_FIXTURE
            )

    if setup_script is not None:
        auto_test.setup_script = setup_script
    if run_setup_script is not None:
        auto_test.run_setup_script = run_setup_script

    db.session.commit()

    return jsonify(auto_test)


@api.route('/auto_tests/<int:auto_test_id>/sets/', methods=['POST'])
@feature_required(Feature.AUTO_TEST)
def create_auto_test_set(auto_test_id: int
                         ) -> JSONResponse[models.AutoTestSet]:
    auto_test = get_or_404(models.AutoTest, auto_test_id)
    auth.ensure_permission(
        CPerm.can_edit_autotest, auto_test.assignment.course_id
    )

    auto_test.sets.append(models.AutoTestSet())
    db.session.commit()

    return jsonify(auto_test.sets[-1])


@api.route(
    '/auto_tests/<int:auto_test_id>/sets/<int:auto_test_set_id>',
    methods=['PATCH']
)
@feature_required(Feature.AUTO_TEST)
def update_auto_test_set(
    auto_test_id: int, auto_test_set_id: int
) -> EmptyResponse:
    auto_test_set = filter_single_or_404(
        models.AutoTestSet,
        models.AutoTestSet.id == auto_test_set_id,
        models.AutoTest.id == auto_test_id,
    )

    auth.ensure_permission(
        CPerm.can_edit_autotest, auto_test_set.auto_test.assignment.course_id
    )

    with get_from_map_transaction(get_json_dict_from_request()) as [get, opt]:
        stop_points = t.cast(
            t.Optional[float], opt('stop_points', numbers.Real, None)
        )  # type: ignore

    if stop_points is not None:
        print('setting stop points to: ', stop_points)
        auto_test_set.stop_points = stop_points

    db.session.commit()

    return make_empty_response()


@api.route(
    '/auto_tests/<int:auto_test_id>/sets/<int:auto_test_set_id>',
    methods=['DELETE']
)
@feature_required(Feature.AUTO_TEST)
def delete_auto_test_set(
    auto_test_id: int, auto_test_set_id: int
) -> EmptyResponse:
    auto_test_set = filter_single_or_404(
        models.AutoTestSet,
        models.AutoTestSet.id == auto_test_set_id,
        models.AutoTest.id == auto_test_id,
    )
    auth.ensure_permission(
        CPerm.can_edit_autotest, auto_test_set.auto_test.assignment.course_id
    )

    db.session.delete(auto_test_set)
    db.session.commit()

    return make_empty_response()


@api.route(
    '/auto_tests/<int:auto_test_id>/sets/<int:auto_test_set_id>/suites/',
    methods=['PATCH']
)
@feature_required(Feature.AUTO_TEST)
def update_or_create_auto_test_suite(auto_test_id: int, auto_test_set_id: int
                                     ) -> JSONResponse[models.AutoTestSuite]:
    auto_test_set = filter_single_or_404(
        models.AutoTestSet,
        models.AutoTestSet.id == auto_test_set_id,
        models.AutoTest.id == auto_test_id,
    )
    auth.ensure_permission(
        CPerm.can_edit_autotest, auto_test_set.auto_test.assignment.course_id
    )

    with get_from_map_transaction(get_json_dict_from_request()) as [get, opt]:
        steps = get('steps', list)
        rubric_row_id = get('rubric_row_id', int)
        network_disabled = get('network_disabled', bool)
        suite_id = opt('id', int, None)

    if suite_id is None:
        suite = models.AutoTestSuite(auto_test_set=auto_test_set)
    else:
        suite = get_or_404(models.AutoTestSuite, suite_id)

    suite.network_disabled = network_disabled
    if suite.rubric_row_id != rubric_row_id:
        if (
            rubric_row_id in
            auto_test_set.auto_test.assignment.locked_rubric_rows
        ):
            raise Exception
        rubric_row = get_or_404(models.RubricRow, rubric_row_id)
        # TODO: This sometimes fails?
        if (
            rubric_row.assignment.id !=
            suite.auto_test_set.auto_test.assignment.id
        ):
            raise Exception
        suite.rubric_row = rubric_row
        if rubric_row.is_selected():
            add_warning(
                'This rubric category is already used for manual grading',
                APIWarnings.IN_USE_RUBRIC_ROW
            )

    new_steps = []
    for idx, step_data in enumerate(steps):
        with get_from_map_transaction(ensure_json_dict(step_data)) as [
            get, opt
        ]:
            step_id = opt('id', int, None)
            data = get('data', dict)
            # TODO: validate this data var
            typ_str = get('type', str)
            name = get('name', str)
            hidden = get('hidden', bool)
            weight = t.cast(float, get('weight', numbers.Real))  # type: ignore

        try:
            step_type = auto_test_handlers[typ_str]
        except KeyError:
            raise APIException(
                'The given test type is not valid',
                f'The given test type "{typ_str}" is not known',
                APICodes.INVALID_PARAM, 400
            )

        if step_id is None:
            step = step_type()
            db.session.add(step)
        else:
            step = get_or_404(
                step_type,
                step_id,
                also_error=lambda obj: not isinstance(obj, step_type),
            )

        step.hidden = hidden
        step.order = idx
        step.name = name
        step.weight = weight

        step.update_data_from_json(data)
        new_steps.append(step)

    suite.steps = new_steps

    db.session.commit()
    return jsonify(suite)


@api.route(
    '/auto_tests/<int:test_id>/sets/<int:set_id>/suites/<int:suite_id>',
    methods=['DELETE']
)
@feature_required(Feature.AUTO_TEST)
def delete_suite(test_id: int, set_id: int, suite_id: int) -> EmptyResponse:
    suite = filter_single_or_404(
        models.AutoTestSuite,
        models.AutoTestSuite.id == suite_id,
        models.AutoTestSet.id == set_id,
        models.AutoTest.id == test_id,
    )
    auth.ensure_permission(
        CPerm.can_edit_autotest,
        suite.auto_test_set.auto_test.assignment.course_id
    )

    db.session.delete(suite)
    db.session.commit()
    return make_empty_response()


@api.route('/auto_tests/<int:auto_test_id>', methods=['GET'])
@feature_required(Feature.AUTO_TEST)
def get_auto_test(auto_test_id: int) -> ExtendedJSONResponse[models.AutoTest]:
    test = get_or_404(models.AutoTest, auto_test_id)
    auth.ensure_can_view_autotest(test)

    return extended_jsonify(
        test, use_extended=(models.AutoTest, models.AutoTestRun)
    )


@api.route('/auto_tests/<int:auto_test_id>/runs/<int:run_id>', methods=['GET'])
@feature_required(Feature.AUTO_TEST)
def get_auto_test_run(auto_test_id: int,
                      run_id: int) -> ExtendedJSONResponse[models.AutoTestRun]:
    run = filter_single_or_404(
        models.AutoTestRun,
        models.AutoTestRun.id == run_id,
        models.AutoTest.id == auto_test_id,
    )
    auth.ensure_can_view_autotest(run.auto_test)
    return extended_jsonify(run, use_extended=models.AutoTestRun)


@api.route('/auto_tests/<int:auto_test_id>/runs/', methods=['POST'])
@feature_required(Feature.AUTO_TEST)
def start_auto_test_run(auto_test_id: int) -> t.Union[JSONResponse[
    t.Mapping[str, None]], ExtendedJSONResponse[models.AutoTestRun]]:
    test = get_or_404(models.AutoTest, auto_test_id)

    auth.ensure_permission(CPerm.can_run_autotest, test.assignment.course_id)

    if test.runs:
        raise APIException(
            'This test already has a run',
            f'The test "{test.id}" already has a run "{test.runs[0].id}"',
            APICodes.INVALID_STATE, 400
        )

    sub_ids = t.cast(
        t.List[t.Tuple[int]],
        test.assignment.get_from_latest_submissions(models.Work.id).all()
    )
    results = [models.AutoTestResult(work_id=sub_id) for sub_id, in sub_ids]
    test.runs.append(models.AutoTestRun(results=results))

    db.session.commit()

    try:
        auth.ensure_can_view_autotest(test)
    except exceptions.PermissionException:
        return jsonify({})
    else:
        return extended_jsonify(test.runs[0], use_extended=models.AutoTestRun)


@api.route(
    '/auto_tests/<int:auto_test_id>/runs/<int:run_id>', methods=['DELETE']
)
@feature_required(Feature.AUTO_TEST)
def delete_auto_test_runs(auto_test_id: int, run_id: int) -> EmptyResponse:
    test = get_or_404(models.AutoTest, auto_test_id)
    auth.ensure_permission(
        CPerm.can_delete_autotest_run, test.assignment.course_id
    )

    run = get_or_404(
        models.AutoTestRun,
        run_id,
        also_error=lambda obj: obj.auto_test_id != test.id,
    )

    if run.runner_id is not None:
        runner_id = run.runner_id
        callback_after_this_request(
            lambda: tasks.remove_auto_test_runner(runner_id.hex)
        )

    run.delete_and_clear_rubric()
    db.session.commit()

    return make_empty_response()


@api.route(
    '/auto_tests/<int:auto_test_id>/runs/<int:run_id>/results/<int:result_id>',
    methods=['GET']
)
@feature_required(Feature.AUTO_TEST)
def get_auto_test_result(auto_test_id: int, run_id: int, result_id: int
                         ) -> ExtendedJSONResponse[models.AutoTestResult]:
    test = get_or_404(models.AutoTest, auto_test_id)
    auth.ensure_can_view_autotest(test)

    def also_error(obj: models.AutoTestResult) -> bool:
        return (
            obj.auto_test_run_id != run_id or obj.run.auto_test_id != test.id
        )

    result = get_or_404(
        models.AutoTestResult,
        result_id,
        also_error=also_error,
    )

    auth.ensure_can_see_grade(result.work)

    return extended_jsonify(result, use_extended=models.AutoTestResult)
