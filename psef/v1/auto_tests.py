import json
import typing as t
import numbers

from flask import request

from . import api
from .. import app, files, models, parsers, auto_test
from ..models import db
from ..helpers import (
    JSONResponse, EmptyResponse, ExtendedJSONResponse, jsonify, get_or_404,
    ensure_json_dict, extended_jsonify, ensure_keys_in_dict,
    make_empty_response, filter_single_or_404, get_files_from_request,
    get_from_map_transaction, get_json_dict_from_request,
    callback_after_this_request
)
from ..exceptions import APICodes, APIException


@api.route('/auto_tests/', methods=['POST'])
def create_auto_test() -> JSONResponse[models.AutoTest]:
    with get_from_map_transaction(get_json_dict_from_request()) as [get, _]:
        assignment_id = get('assignment_id', int)

    # TODO: permission

    auto_test = models.AutoTest(
        assignment=get_or_404(models.Assignment, assignment_id),
        setup_script='',
        finalize_script='',
    )
    db.session.add(auto_test)
    db.session.commit()
    return jsonify(auto_test)


@api.route('/auto_tests/<int:auto_test_id>', methods=['DELETE'])
def delete_auto_test(auto_test_id: int) -> EmptyResponse:
    auto_test = get_or_404(models.AutoTest, auto_test_id)

    for f in auto_test.fixtures:
        db.session.delete(f)
        callback_after_this_request(f.delete_from_disk)

    db.session.delete(auto_test)
    db.session.commit()

    return make_empty_response()


@api.route(
    '/auto_tests/<int:auto_test_id>/fixtures/<int:fixture_id>/hide',
    methods=['POST', 'DELETE']
)
def hide_or_open_fixture(auto_test_id: int, fixture_id: int) -> EmptyResponse:
    fixture = filter_single_or_404(
        models.AutoTestFixture,
        models.AutoTest.id == auto_test_id,
        models.AutoTestFixture.id == fixture_id,
    )

    fixture.hidden = request.method == 'POST'
    db.session.commit()

    return make_empty_response()


@api.route('/auto_tests/<int:auto_test_id>', methods=['PATCH'])
def update_or_create_auto_test(auto_test_id: int
                               ) -> JSONResponse[models.AutoTest]:
    auto_test = get_or_404(models.AutoTest, auto_test_id)

    # TODO: Permission check
    content = ensure_json_dict(
        ('json' in request.files and json.loads(request.files['json'].read()))
        or request.get_json()
    )

    with get_from_map_transaction(content) as [get, optional_get]:
        old_fixtures = optional_get('fixtures', list, None)
        base_systems = optional_get('base_systems', list, None)
        finalize_script = optional_get('finalize_script', str, None)
        setup_script = optional_get('setup_script', str, None)
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
        files.fix_duplicate_filenames(auto_test.fixtures)

    if setup_script is not None:
        auto_test.setup_script = setup_script

    if finalize_script is not None:
        auto_test.finalize_script = finalize_script

    if base_systems is not None:
        new_base_systems = []
        for base_system in base_systems:
            with get_from_map_transaction(ensure_json_dict(base_system)) as [
                get, _
            ]:
                base_system_id = get('id', int)
                base_system_name = get('name', str)

            new_base_system = app.auto_test_base_systems.get(
                base_system_id, {}
            )
            if (
                base_system_id not in app.auto_test_base_systems or
                new_base_system.get('name') != base_system_name
            ):
                raise Exception
            new_base_systems.append(
                {key: new_base_system[key]
                 for key in ['id', 'name', 'group']}
            )
        if len(new_base_systems) != len(
            set(a['group'] for a in new_base_systems)
        ):
            raise Exception
        auto_test.base_systems = new_base_systems

    db.session.commit()

    return jsonify(auto_test)


@api.route('/auto_tests/<int:auto_test_id>/sets/', methods=['POST'])
def create_auto_test_set(auto_test_id: int
                         ) -> JSONResponse[models.AutoTestSet]:
    auto_test = get_or_404(models.AutoTest, auto_test_id)
    # TODO: Permission check

    auto_test.sets.append(models.AutoTestSet())
    db.session.commit()

    return jsonify(auto_test.sets[-1])


@api.route(
    '/auto_tests/<int:auto_test_id>/sets/<int:auto_test_set_id>',
    methods=['PATCH']
)
def update_auto_test_set(
    auto_test_id: int, auto_test_set_id: int
) -> EmptyResponse:
    auto_test_set = filter_single_or_404(
        models.AutoTestSet,
        models.AutoTestSet.id == auto_test_set_id,
        models.AutoTest.id == auto_test_id,
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
def delete_auto_test_set(
    auto_test_id: int, auto_test_set_id: int
) -> EmptyResponse:
    auto_test_set = filter_single_or_404(
        models.AutoTestSet,
        models.AutoTestSet.id == auto_test_set_id,
        models.AutoTest.id == auto_test_id,
    )
    # TODO: Permission check

    db.session.delete(auto_test_set)
    db.session.commit()

    return make_empty_response()


@api.route(
    '/auto_tests/<int:auto_test_id>/sets/<int:auto_test_set_id>/suites/',
    methods=['PATCH']
)
def update_or_create_auto_test_suite(auto_test_id: int, auto_test_set_id: int
                                     ) -> JSONResponse[models.AutoTestSuite]:
    auto_test_set = filter_single_or_404(
        models.AutoTestSet,
        models.AutoTestSet.id == auto_test_set_id,
        models.AutoTest.id == auto_test_id,
    )
    # TODO: Permission check

    with get_from_map_transaction(get_json_dict_from_request()) as [get, opt]:
        steps = get('steps', list)
        rubric_row_id = get('rubric_row_id', int)
        suite_id = opt('id', int, None)

    if suite_id is None:
        suite = models.AutoTestSuite(auto_test_set=auto_test_set)
    else:
        suite = get_or_404(models.AutoTestSuite, suite_id)

    rubric_row = get_or_404(models.RubricRow, rubric_row_id)
    if rubric_row.assignment.id != suite.auto_test_set.auto_test.assignment.id:
        raise Exception
    suite.rubric_row = rubric_row

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

        step_type = auto_test.auto_test_handlers.get(typ_str)
        if step_type is None:
            raise APIException(
                'The given test type is not valid',
                f'The given test type "{typ_str}" is not known',
                APICodes.INVALID_PARAM, 400
            )

        if step_id is None:
            step = models.AutoTestStep(name=name, weight=weight)
            db.session.add(step)
            step.test_type = step_type
        else:
            step = get_or_404(models.AutoTestStep, step_id)
            if step.test_type != step_type:
                raise APIException(
                    'You cannot change the test type of a step after creation',
                    (
                        f'Trying to change the test type to "{typ_str}" for'
                        f' step "{step_id}" is not valid'
                    ), APICodes.INVALID_PARAM, 400
                )

        step.hidden = hidden
        step.order = idx
        step.name = name
        step.weight = weight

        step.update_from_json(data)
        new_steps.append(step)
    suite.steps = new_steps

    db.session.commit()
    return jsonify(suite)


@api.route(
    '/auto_tests/<int:test_id>/sets/<int:set_id>/suites/<int:suite_id>',
    methods=['DELETE']
)
def delete_suite(test_id: int, set_id: int, suite_id: int) -> EmptyResponse:
    suite = filter_single_or_404(
        models.AutoTestSuite,
        models.AutoTestSuite.id == suite_id,
        models.AutoTestSet.id == set_id,
        models.AutoTest.id == test_id,
    )

    db.session.delete(suite)
    db.session.commit()
    return make_empty_response()
    # TODO: Permission check


@api.route('/auto_tests/<int:auto_test_id>', methods=['GET'])
def get_auto_test(auto_test_id: int) -> ExtendedJSONResponse[models.AutoTest]:
    return extended_jsonify(
        get_or_404(models.AutoTest, auto_test_id),
        use_extended=(models.AutoTest, models.AutoTestRun)
    )


@api.route('/auto_tests/<int:auto_test_id>/runs/<int:run_id>', methods=['GET'])
def get_auto_test_run(auto_test_id: int,
                      run_id: int) -> ExtendedJSONResponse[models.AutoTestRun]:
    run = filter_single_or_404(
        models.AutoTestRun,
        models.AutoTestRun.id == run_id,
        models.AutoTest.id == auto_test_id,
    )
    return extended_jsonify(run, use_extended=models.AutoTestRun)


@api.route('/auto_tests/<int:auto_test_id>/runs/', methods=['POST'])
def start_auto_test_run(auto_test_id: int
                        ) -> ExtendedJSONResponse[models.AutoTestRun]:
    test = get_or_404(models.AutoTest, auto_test_id)
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

    return extended_jsonify(test.runs[0], use_extended=models.AutoTestRun)


@api.route(
    '/auto_tests/<int:auto_test_id>/runs/<int:run_id>', methods=['DELETE']
)
def delete_auto_test_runs(auto_test_id: int, run_id: int) -> EmptyResponse:
    run = filter_single_or_404(
        models.AutoTestRun,
        models.AutoTestRun.id == run_id,
        models.AutoTest.id == auto_test_id,
    )
    db.session.delete(run)
    db.session.commit()
    return make_empty_response()


@api.route(
    '/auto_tests/<int:auto_test_id>/runs/<int:run_id>/results/<int:result_id>',
    methods=['GET']
)
def get_auto_test_result(auto_test_id: int, run_id: int, result_id: int
                         ) -> ExtendedJSONResponse[models.AutoTestResult]:
    result = filter_single_or_404(
        models.AutoTestResult,
        models.AutoTestResult.id == result_id,
        models.AutoTestRun.id == run_id,
        models.AutoTest.id == auto_test_id,
    )
    return extended_jsonify(result, use_extended=models.AutoTestResult)
