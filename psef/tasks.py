"""
This module defines all celery tasks. It is very important that you DO NOT
change the way parameters are used or the parameters provided in existing tasks
as there may tasks left in the old queue. Instead create a new task and change
the mapping of the variables at the bottom of this file.

SPDX-License-Identifier: AGPL-3.0-only
"""
import os
import json
import uuid
import shutil
import typing as t
import datetime
import tempfile
import itertools
from operator import itemgetter

import structlog
from flask import Flask
from celery import signals, current_task
from requests import HTTPError
from sqlalchemy.orm import contains_eager
from mypy_extensions import NamedArg, DefaultNamedArg
from celery.schedules import crontab

import psef as p
import cg_celery
import cg_logger
from cg_dt_utils import DatetimeWithTimezone
from cg_sqlalchemy_helpers.types import DbColumn

logger = structlog.get_logger()

celery = cg_celery.CGCelery('psef', signals)  # pylint: disable=invalid-name


def init_app(app: Flask) -> None:
    celery.init_flask_app(app)


@celery.on_after_configure.connect
def _setup_periodic_tasks(sender: t.Any, **_: object) -> None:
    logger.info('Setting up periodic tasks')
    sender.add_periodic_task(
        crontab(minute='*/15'),
        _run_autotest_batch_runs_1.si(),
    )


@celery.task
def _lint_instances_1(
    linter_name: str,
    cfg: str,
    linter_instance_ids: t.Sequence[str],
) -> None:
    p.linters.LinterRunner(
        p.linters.get_linter_by_name(linter_name),
        cfg,
    ).run(linter_instance_ids)


# This task acks late and retries on exceptions. For the exact meaning of these
# variables see the celery documentation. But basically ``acks_late`` means
# that a task will only be removed from the queue AFTER it has finished
# processing, if the worker dies during processing it will simply restart. The
# ``max_retry`` parameter means that if the worker throws an exception during
# processing the task will also be retried, with a maximum of 10. The
# ``reject_on_worker_lost`` means that if a worker suddenly dies while
# processing the task (if the machine fails, or if the main process is killed
# with the ``KILL`` signal) the task will also be retried.
@celery.task(acks_late=True, max_retries=10, reject_on_worker_lost=True)  # pylint: disable=unexpected-keyword-arg,no-value-for-parameter
def _passback_grades_1(
    submission_ids: t.Sequence[int],
    *,
    assignment_id: int = None,
    initial: bool = False
) -> None:
    if not submission_ids:  # pragma: no cover
        return

    assignment = p.models.Assignment.query.filter_by(
        id=assignment_id
    ).with_for_update().one_or_none()
    if assignment is None:  # pragma: no cover
        subs = p.models.Work.query.filter(
            t.cast(p.models.DbColumn[int], p.models.Work.id).in_(
                submission_ids,
            ),
            ~p.models.Work.deleted,
        ).order_by(
            p.models.Work.user_id,
            t.cast(DbColumn[object], p.models.Work.created_at).desc()
        ).all()
    else:
        subs = assignment.get_all_latest_submissions().filter(
            t.cast(DbColumn[int], p.models.Work.id).in_(submission_ids)
        ).all()

    found_ids = [s.id for s in subs]
    logger.info(
        'Passback grades',
        gotten_submissions=submission_ids,
        found_submissions=found_ids,
        all_found=len(subs) == len(submission_ids),
        difference=list(set(submission_ids) ^ set(found_ids))
    )

    for sub in subs:
        sub.passback_grade(initial=initial)

    p.models.db.session.commit()


@celery.task
def _delete_submission_1(work_id: int, assignment_id: int) -> None:
    assignment = p.models.Assignment.query.filter_by(
        id=assignment_id
    ).with_for_update().one_or_none()
    if assignment is None:
        logger.info('Could not find assignment', assignment_id=assignment_id)
        return
    if assignment.course.lti_provider is None:
        logger.info(
            'Not an LTI submission, ignoring', assignment_id=assignment_id
        )
        return

    # TODO: This has a bug: if a user has a group submission, that is already
    # deleted, and now his/her latest personal submission is deleted, this
    # personal submission is not found, as we think the deleted group
    # submission (which we ignore) is the latest submission.
    # TODO: Another possible bug is that if a user has two submissions, and the
    # latest is already deleted, and now we delete the new latest this is also
    # not registered as the latest submission.
    # In other words: this code works for common cases, but is hopelessly
    # broken for all other cases :(
    sub = assignment.get_all_latest_submissions(include_deleted=True).filter(
        p.models.Work.id == work_id
    ).one_or_none()

    if sub is None:
        logger.info('Could not find submission', work_id=work_id)
        return
    logger.info('Deleting grade for submission', work_id=sub.id)
    assignment.course.lti_provider.delete_grade_for_submission(sub)


@celery.task
def _send_reminder_mails_1(assignment_id: int) -> None:
    assig = p.models.Assignment.query.get(assignment_id)

    if assig is None or None in {assig.done_type, assig.reminder_email_time}:
        return

    finished = set(g.user_id for g in assig.finished_graders)

    to_mail: t.Iterable[int]

    if assig.done_type == p.models.AssignmentDoneType.assigned_only:
        to_mail = assig.get_assigned_grader_ids()
    elif assig.done_type == p.models.AssignmentDoneType.all_graders:
        to_mail = map(itemgetter(1), assig.get_all_graders(sort=False))

    with p.mail.mail.connect() as conn:
        for user_id in to_mail:
            user = p.models.User.query.get(user_id)
            if user is None or user.id in finished:
                continue

            try:
                p.mail.send_grade_reminder_email(
                    assig,
                    user,
                    conn,
                )
            # pylint: disable=broad-except
            except Exception:  # pragma: no cover
                # This happens if mail sending fails or if the user has no
                # e-mail address.
                # TODO: make this exception more specific
                logger.warning(
                    'Could not send email',
                    receiving_user_id=user_id,
                    exc_info=True
                )


@celery.task
def _send_done_mail_1(assignment_id: int) -> None:
    assig = p.models.Assignment.query.get(assignment_id)

    if assig is not None and assig.done_email is not None:
        p.mail.send_whopie_done_email(assig)


@celery.task
def _send_grader_status_mail_1(
    assignment_id: int,
    user_id: int,
) -> None:
    assig = p.models.Assignment.query.get(assignment_id)
    user = p.models.User.query.get(user_id)

    if assig and user:
        p.mail.send_grader_status_changed_mail(assig, user)


@celery.task
def _run_plagiarism_control_1(  # pylint: disable=too-many-branches,too-many-statements
    plagiarism_run_id: int,
    main_assignment_id: int,
    old_assignment_ids: t.List[int],
    call_args: t.List[str],
    base_code_dir: t.Optional[str],
    csv_location: str,
) -> None:
    def at_end() -> None:
        if base_code_dir:
            shutil.rmtree(base_code_dir)

    def set_state(state: p.models.PlagiarismState) -> None:
        assert plagiarism_run
        plagiarism_run.state = state
        p.models.db.session.commit()

    with p.helpers.defer(
        at_end,
    ), tempfile.TemporaryDirectory(
    ) as result_dir, tempfile.TemporaryDirectory(
    ) as tempdir, tempfile.TemporaryDirectory() as archive_dir:
        plagiarism_run = p.models.PlagiarismRun.query.get(plagiarism_run_id)
        if plagiarism_run is None:  # pragma: no cover
            logger.info(
                'Plagiarism run was already deleted',
                plagiarism_run_id=plagiarism_run_id,
            )
            return
        set_state(p.models.PlagiarismState.started)

        supports_progress = plagiarism_run.plagiarism_cls.supports_progress()
        progress_prefix = str(uuid.uuid4())

        archival_arg_present = '{ archive_dir }' in call_args
        if '{ restored_dir }' in call_args:
            call_args[call_args.index('{ restored_dir }')] = tempdir
        if '{ result_dir }' in call_args:
            call_args[call_args.index('{ result_dir }')] = result_dir
        if archival_arg_present:
            call_args[call_args.index('{ archive_dir }')] = archive_dir
        if base_code_dir:
            call_args[call_args.index('{ base_code_dir }')] = base_code_dir
        if supports_progress:
            call_args[call_args.index('{ progress_prefix }')] = progress_prefix

        file_lookup_tree: t.Dict[int, p.files.FileTree[int]] = {}
        submission_lookup: t.Dict[str, int] = {}
        old_subs: t.Set[int] = set()

        assig_ids = [main_assignment_id, *old_assignment_ids]
        assigs = p.helpers.get_in_or_error(
            p.models.Assignment,
            t.cast(p.models.DbColumn[int], p.models.Assignment.id),
            assig_ids,
        )

        chained: t.List[t.List[p.models.Work]] = []
        for assig in assigs:
            chained.append(assig.get_all_latest_submissions().all())
            if assig.id == main_assignment_id:
                plagiarism_run.submissions_total = len(chained[-1])
                p.models.db.session.commit()

        for sub in itertools.chain.from_iterable(chained):
            main_assig = sub.assignment_id == main_assignment_id

            dir_name = (
                f'{sub.user.name} || {sub.assignment_id}'
                f'-{sub.id}-{sub.user_id}'
            )
            submission_lookup[dir_name] = sub.id
            parent = p.files.safe_join(tempdir, dir_name)

            if not main_assig:
                old_subs.add(sub.id)
                if archival_arg_present:
                    parent = os.path.join(archive_dir, dir_name)

            os.mkdir(parent)
            part_tree = p.files.restore_directory_structure(sub, parent)
            file_lookup_tree[sub.id] = p.files.FileTree(
                name=dir_name,
                id=-1,
                entries=[part_tree],
            )

        if supports_progress:
            set_state(p.models.PlagiarismState.parsing)
        else:  # pragma: no cover
            # We don't have any providers not supporting progress
            set_state(p.models.PlagiarismState.running)

        def got_output(line: str) -> bool:
            if not supports_progress:  # pragma: no cover
                return False

            assert plagiarism_run is not None
            new_val = plagiarism_run.plagiarism_cls.get_progress_from_line(
                progress_prefix, line
            )
            if new_val is not None:
                cur, tot = new_val
                if (
                    cur == tot and
                    plagiarism_run.state == p.models.PlagiarismState.parsing
                ):
                    set_state(p.models.PlagiarismState.comparing)
                    plagiarism_run.submissions_done = 0
                else:
                    val = cur + (plagiarism_run.submissions_total or 0) - tot
                    plagiarism_run.submissions_done = val
                p.models.db.session.commit()
                return True
            return False

        try:
            ok, stdout = p.helpers.call_external(
                call_args, got_output, nice_level=10
            )
        # pylint: disable=broad-except
        except Exception:  # pragma: no cover
            set_state(p.models.PlagiarismState.crashed)
            raise
        logger.info(
            'Plagiarism call finished',
            finished_successfully=ok,
            captured_stdout=stdout
        )

        set_state(p.models.PlagiarismState.finalizing)

        plagiarism_run.log = stdout
        if ok:
            csv_file = os.path.join(result_dir, csv_location)
            csv_file = plagiarism_run.plagiarism_cls.transform_csv(csv_file)

            for case in p.plagiarism.process_output_csv(
                submission_lookup, old_subs, file_lookup_tree, csv_file
            ):
                plagiarism_run.cases.append(case)
            set_state(p.models.PlagiarismState.done)
        else:
            set_state(p.models.PlagiarismState.crashed)
        p.models.db.session.commit()


@celery.task
def _run_autotest_batch_runs_1() -> None:
    now = DatetimeWithTimezone.utcnow()
    # Limit the amount of runs, this way we never accidentally overload the
    # server by doing a large amount of batch run.
    max_runs = p.app.config['AUTO_TEST_MAX_CONCURRENT_BATCH_RUNS']

    runs = p.models.AutoTestRun.query.join(
        p.models.AutoTestRun.auto_test
    ).join(p.models.Assignment).filter(
        t.cast(DbColumn[bool], p.models.AutoTestRun.batch_run_done).is_(False),
        p.models.Assignment.deadline < now,
    ).options(contains_eager(p.models.AutoTestRun.auto_test)).order_by(
        p.models.Assignment.deadline
    ).with_for_update().limit(max_runs).all()

    logger.info('Running batch run', run_ids=[r.id for r in runs])

    for run in runs:
        run.do_batch_run()

    p.models.db.session.commit()


@celery.task(
    autoretry_for=(HTTPError, ),
    retry_backoff=True,
    retry_kwargs={'max_retries': 15}
)
def _notify_broker_of_new_job_1(
    run_id: t.Union[int, p.models.AutoTestRun],
    wanted_runners: t.Optional[int] = 1
) -> None:
    if isinstance(run_id, int):
        run = p.models.AutoTestRun.query.filter_by(
            id=run_id
        ).with_for_update().one_or_none()
        if wanted_runners is None:
            wanted_runners = run.get_amount_of_needed_runners()

        if run is None:
            logger.warning('Trying to start run that does not exist')
            return
    else:
        run = run_id

    with p.helpers.BrokerSession() as ses:
        req = ses.put(
            '/api/v1/jobs/',
            json={
                'job_id': run.get_job_id(),
                'wanted_runners': wanted_runners,
                'metadata': run.get_broker_metadata(),
            },
        )
        req.raise_for_status()
        try:
            run.runners_requested = req.json().get(
                'wanted_runners', max(wanted_runners, 1)
            )
        except json.decoder.JSONDecodeError:
            run.runners_requested = max(wanted_runners, 1)
        p.models.db.session.commit()

    _update_latest_results_in_broker_1.delay(run.id)


@celery.task(
    autoretry_for=(HTTPError, ),
    retry_backoff=True,
    retry_kwargs={'max_retries': 15}
)
def _notify_broker_kill_single_runner_1(
    run_id: int, runner_hex_id: str
) -> None:
    run = p.models.AutoTestRun.query.filter_by(
        id=run_id
    ).with_for_update().one_or_none()

    runner_id = uuid.UUID(hex=runner_hex_id)
    runner = p.models.AutoTestRunner.query.with_for_update().get(runner_id)

    if run is None:
        logger.warning('Run could not be found')
        return
    elif runner is None:
        logger.warning('Runner could not be found')
        return

    with p.helpers.BrokerSession() as ses:
        ses.delete(
            f'/api/v1/jobs/{runner.job_id}/runners/',
            json={
                'ipaddr': runner.ipaddr,
            }
        ).raise_for_status()
        run.runners_requested -= 1
        p.models.db.session.commit()


@celery.task(
    autoretry_for=(HTTPError, ),
    retry_backoff=True,
    retry_kwargs={'max_retries': 15}
)
def _notify_broker_end_of_job_1(
    job_id: str, ignore_non_existing: bool = False
) -> None:
    ignore = str(ignore_non_existing).lower()
    with p.helpers.BrokerSession() as ses:
        ses.delete(f'/api/v1/jobs/{job_id}?ignore_non_existing={ignore}'
                   ).raise_for_status()


@celery.task
def _check_heartbeat_stop_test_runner_1(auto_test_runner_id: str) -> None:
    runner_id = uuid.UUID(hex=auto_test_runner_id)

    runner = p.models.AutoTestRunner.query.get(runner_id)
    if runner is None:
        logger.info('Runner not found', runner=runner)
        return
    elif runner.run is None:
        logger.info('Runner already reset', runner=runner)
        return

    interval = p.app.config['AUTO_TEST_HEARTBEAT_INTERVAL']
    max_missed = p.app.config['AUTO_TEST_HEARTBEAT_MAX_MISSED']
    max_interval = datetime.timedelta(seconds=interval * max_missed)
    needed_time = DatetimeWithTimezone.utcnow() - max_interval
    expired = runner.last_heartbeat < needed_time

    logger.info(
        'Checking heartbeat',
        last_heartbeat=runner.last_heartbeat.isoformat(),
        deadline=needed_time.isoformat(),
        max_internval=max_interval.total_seconds(),
        expired=expired,
    )

    # In this case the heartbeat received was recently, so we schedule this
    # task again.
    if not expired:
        check_heartbeat_auto_test_run(
            (runner.id.hex, ), eta=runner.last_heartbeat + max_interval
        )
        return

    run = p.models.AutoTestRun.query.filter_by(id=runner.run_id
                                               ).with_for_update().one()
    run.stop_runners([runner])
    p.models.db.session.commit()


@celery.task
def _adjust_amount_runners_1(auto_test_run_id: int) -> None:
    run = p.models.AutoTestRun.query.filter_by(
        id=auto_test_run_id
    ).with_for_update().one_or_none()

    if run is None:
        logger.warning('Run to adjust not found')
        return

    requested_amount = run.runners_requested
    needed_amount = run.get_amount_needed_runners()
    with cg_logger.bound_to_logger(
        requested_amount=requested_amount, needed_amount=needed_amount
    ):
        if needed_amount == requested_amount:
            logger.info('No new runners needed')
            return
        elif needed_amount == 0 and run.runners_requested < 2:
            # If we have requested more than 2 runners we should decrease this,
            # so do send this request to the broker.
            logger.info("We don't need any runners")
            return
        elif needed_amount > requested_amount:
            logger.info('We need more runners')
        else:
            logger.info('We have requested too many runners')

        _notify_broker_of_new_job_1(run, needed_amount)


@celery.task
def _kill_runners_and_adjust_1(
    run_id: int, runners_to_kill_hex_ids: t.List[str]
) -> None:
    for runner_hex_id in runners_to_kill_hex_ids:
        _notify_broker_kill_single_runner_1(run_id, runner_hex_id)
    _adjust_amount_runners_1(run_id)


@celery.task
def _update_latest_results_in_broker_1(auto_test_run_id: int) -> None:
    m = p.models  # pylint: disable=invalid-name

    run = m.AutoTestRun.query.get(auto_test_run_id)
    if run is None:
        logger.info('Run not found', run_id=auto_test_run_id)
        return

    def get_latest_date(
        state: m.AutoTestStepResultState,
        col: t.Union[DbColumn[DatetimeWithTimezone], DbColumn[
            t.Optional[DatetimeWithTimezone]]],
        oldest: bool = True
    ) -> t.Optional[str]:
        date = m.db.session.query(col).filter_by(
            auto_test_run_id=auto_test_run_id,
            state=state,
        ).order_by(col if oldest else col.desc()).first()

        if date is None or date[0] is None:
            return None
        return date[0].isoformat()

    # yapf: disable
    results = {
        'not_started': get_latest_date(
            m.AutoTestStepResultState.not_started,
            m.AutoTestResult.updated_at,
        ),
        'running': get_latest_date(
            m.AutoTestStepResultState.running,
            m.AutoTestResult.started_at,
        ),
        'passed': get_latest_date(
            m.AutoTestStepResultState.passed,
            m.AutoTestResult.updated_at,
            False,
        ),
    }
    # yapf: enable

    with p.helpers.BrokerSession() as ses:
        ses.put(
            '/api/v1/jobs/',
            json={
                'job_id': run.get_job_id(),
                'metadata': {
                    'results': results,
                },
                'error_on_create': True,
            },
        ).raise_for_status()


@celery.task
def _clone_commit_as_submission_1(
    unix_timestamp: float,
    clone_data_as_dict: t.Dict[str, t.Any],
) -> None:
    """Clone a repository and create a submission from its files.

    .. warning::

        This function **does not** check if the user has permission to create a
        submission, so this should be done by the caller.

    :param unix_timestamp: The date the submission should be created at. The
        rationale for passing this is that a user might have permission to
        create a submission at this time, but not at the time of the commit (or
        vica versa). And as commit times cannot be trusted this should be
        given explicitly.
    :param clone_data_as_dict: A :class:`p.models.GitCloneData` as a
        dictionary, including private data.
    :returns: Nothing.
    """
    clone_data = p.models.GitCloneData(**clone_data_as_dict)

    webhook = p.models.WebhookBase.query.get(clone_data.webhook_id)
    if webhook is None:
        logger.warning('Could not find webhook')
        return

    assignment = p.models.Assignment.query.filter_by(id=webhook.assignment_id
                                                     ).with_for_update().one()

    created_at = DatetimeWithTimezone.utcfromtimestamp(unix_timestamp)

    with webhook.written_private_key() as fname, tempfile.TemporaryDirectory(
    ) as tmpdir:
        ssh_username = webhook.ssh_username
        assert ssh_username is not None
        program = p.helpers.format_list(
            p.current_app.config['GIT_CLONE_PROGRAM'],
            clone_url=clone_data.clone_url,
            commit=clone_data.commit,
            out_dir=tmpdir,
            ssh_key=fname,
            ssh_username=ssh_username,
            git_branch=clone_data.branch,
        )

        success, output = p.helpers.call_external(program)
        logger.info(
            'Called external clone program',
            successful=success,
            command_output=output
        )
        if not success:
            return

        p.archive.Archive.replace_symlinks(tmpdir)
        tree = p.extract_tree.ExtractFileTree(
            values=p.files.rename_directory_structure(
                tmpdir, p.app.max_file_size
            ).values,
            name=clone_data.repository_name.replace('/', ' - '),
            parent=None
        )
        logger.info('Creating submission')
        work = p.models.Work.create_from_tree(
            assignment, webhook.user, tree, created_at=created_at
        )
        work.origin = p.models.WorkOrigin[clone_data.type]
        work.extra_info = clone_data.get_extra_info()
        p.models.db.session.commit()


@celery.task
def _delete_file_at_time_1(
    filename: str, in_mirror_dir: bool, deletion_time: str
) -> None:
    if current_task.maybe_delay_task(
        DatetimeWithTimezone.fromisoformat(deletion_time)
    ):
        return

    if in_mirror_dir:
        root = p.app.config['MIRROR_UPLOAD_DIR']
    else:  # pragma: no cover
        # The case outside of the mirror_upload_dir is not yet used
        root = p.app.config['UPLOAD_DIR']

    filename = p.files.safe_join(root, filename)
    if os.path.isfile(filename):
        # There is a race condition here (file is removed in this small space),
        # but we don't care as it is removed in that case
        try:
            os.unlink(filename)
        except FileNotFoundError:  # pragma: no cover
            pass


@celery.task
def _add_1(first: int, second: int) -> int:  # pragma: no cover
    """This function is used for testing if celery works. What it actually does
    is completely irrelevant.
    """
    return first + second


passback_grades = _passback_grades_1.delay  # pylint: disable=invalid-name
lint_instances = _lint_instances_1.delay  # pylint: disable=invalid-name
add = _add_1.delay  # pylint: disable=invalid-name
send_done_mail = _send_done_mail_1.delay  # pylint: disable=invalid-name
send_grader_status_mail = _send_grader_status_mail_1.delay  # pylint: disable=invalid-name
run_plagiarism_control = _run_plagiarism_control_1.delay  # pylint: disable=invalid-name
notify_broker_of_new_job = _notify_broker_of_new_job_1.delay  # pylint: disable=invalid-name
notify_broker_end_of_job = _notify_broker_end_of_job_1.delay  # pylint: disable=invalid-name
notify_broker_kill_single_runner = _notify_broker_kill_single_runner_1.delay  # pylint: disable=invalid-name
adjust_amount_runners = _adjust_amount_runners_1.delay  # pylint: disable=invalid-name
kill_runners_and_adjust = _kill_runners_and_adjust_1.delay  # pylint: disable=invalid-name
delete_submission = _delete_submission_1.delay  # pylint: disable=invalid-name
update_latest_results_in_broker = _update_latest_results_in_broker_1.delay  # pylint: disable=invalid-name
clone_commit_as_submission = _clone_commit_as_submission_1.delay  # pylint: disable=invalid-name
delete_file_at_time = _delete_file_at_time_1.delay  # pylint: disable=invalid-name

send_reminder_mails: t.Callable[
    [t.Tuple[int],
     NamedArg(t.Optional[DatetimeWithTimezone], 'eta')], t.
    Any] = _send_reminder_mails_1.apply_async  # pylint: disable=invalid-name

check_heartbeat_auto_test_run: t.Callable[
    [t.Tuple[str],
     DefaultNamedArg(t.Optional[DatetimeWithTimezone], 'eta')], t.
    Any] = _check_heartbeat_stop_test_runner_1.apply_async  # pylint: disable=invalid-name
