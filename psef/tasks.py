"""
This module defines all celery tasks. It is very important that you DO NOT
change the way parameters are used or the parameters provided in existing tasks
as there may tasks left in the old queue. Instead create a new task and change
the mapping of the variables at the bottom of this file.

SPDX-License-Identifier: AGPL-3.0-only
"""
import os
import uuid
import shutil
import typing as t
import datetime
import tempfile
import itertools
from operator import itemgetter

import structlog
from flask import g
from celery import Celery as _Celery
from celery import signals
from mypy_extensions import NamedArg

import psef as p

logger = structlog.get_logger()


@signals.before_task_publish.connect
def __celery_before_task_publish(
    sender: str, headers: object, **_: object
) -> None:  # pragma: no cover
    logger.info('Publishing task', sender=sender, headers=headers)


@signals.after_task_publish.connect
def __celery_after_task_publish(
    sender: str, headers: object, **_: object
) -> None:  # pragma: no cover
    logger.info('Published task', sender=sender, headers=headers)


@signals.task_success.connect
def __celery_success(**kwargs: object) -> None:
    logger.info(
        'Task finished',
        result=kwargs['result'],
    )


@signals.task_failure.connect
def __celery_failure(**_: object) -> None:  # pragma: no cover
    logger.error(
        'Task failed',
        exc_info=True,
    )


@signals.task_revoked.connect
def __celery_revoked(**kwargs: object) -> None:  # pragma: no cover
    logger.info(
        'Task revoked',
        terminated=kwargs['terminated'],
        signum=kwargs['signum'],
        expired=kwargs['expired'],
    )


@signals.task_unknown.connect
def __celery_unkown(**kwargs: object) -> None:  # pragma: no cover
    logger.warning(
        'Unknown task received',
        task_name=kwargs['name'],
        request_id=kwargs['id'],
        raw_message=kwargs['message'],
    )


@signals.task_rejected.connect
def __celery_rejected(**kwargs: object) -> None:  # pragma: no cover
    logger.warning(
        'Rejected task received',
        raw_message=kwargs['message'],
    )


# pylint: disable=missing-docstring,no-self-use,pointless-statement
if t.TYPE_CHECKING:  # pragma: no cover
    T = t.TypeVar('T', bound=t.Callable)

    class CeleryTask(t.Generic[T]):  # pylint: disable=unsubscriptable-object
        @property
        def delay(self) -> T:
            # This hax is for sphinx as it can't parse the source otherwise
            return lambda *args, **kwargs: None  # type: ignore

        @property
        def apply_async(self) -> t.Any:
            ...

    class Celery:
        def __init__(self, _name: str) -> None:
            self.conf: t.MutableMapping[t.Any, t.Any] = {}
            self.control: t.Any

        def init_app(self, _app: t.Any) -> None:
            ...

        @t.overload
        def task(self, _callback: T) -> CeleryTask[T]:
            ...

        @t.overload
        def task(  # pylint: disable=function-redefined,unused-argument
            self,
            **kwargs: t.Union[int, bool]
        ) -> t.Callable[[T], CeleryTask[T]]:
            ...

        def task(self, *args: object, **kwargs: object) -> t.Any:  # pylint: disable=function-redefined,unused-argument
            # `CeleryTask()` is returned here as this code is also executed
            # when generating the documentation.
            if len(args) == 1:
                return CeleryTask()
            else:
                return self.task
else:
    Celery = _Celery
# pylint: enable=missing-docstring,no-self-use,pointless-statement


class MyCelery(Celery):
    """A subclass of celery that makes sure tasks are always called with a
    flask app context
    """

    def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
        self._flask_app: t.Any = None
        super(MyCelery, self).__init__(*args, **kwargs)

        if t.TYPE_CHECKING:  # pragma: no cover

            class TaskBase:
                """Example task base for Mypy annotations
                """
                request: t.Any
                name: str
        else:
            # self.Task is available in the `Celery` object.
            TaskBase = self.Task  # pylint: disable=access-member-before-definition,invalid-name

        outer_self = self

        class _ContextTask(TaskBase):
            abstract = True

            def __call__(self, *args: t.Any, **kwargs: t.Any) -> t.Any:
                # This is not written by us but taken from here:
                # https://web.archive.org/web/20150617151604/http://slides.skien.cc/flask-hacks-and-best-practices/#15

                # pylint: disable=protected-access
                assert outer_self._flask_app  # pragma: no cover

                log = logger.new(
                    request_id=self.request.id,
                    in_celery=True,
                    task_name=self.name,
                    # pylint: disable=protected-access
                    base_url=outer_self._flask_app.config['EXTERNAL_URL'],
                )

                log.info('Starting task', args=args, kwargs=kwargs)

                if outer_self._flask_app.config['TESTING']:
                    g.request_id = self.request.id
                    g.queries_amount = 0
                    g.queries_total_duration = 0
                    g.queries_max_duration = None
                    g.query_start = None
                    result = TaskBase.__call__(self, *args, **kwargs)
                    logger.bind(
                        queries_amount=g.queries_amount,
                        queries_max_duration=g.queries_max_duration,
                        queries_total_duration=g.queries_total_duration,
                    )
                    return result
                with outer_self._flask_app.app_context():  # pragma: no cover
                    g.request_id = self.request.id
                    g.queries_amount = 0
                    g.queries_total_duration = 0
                    g.queries_max_duration = None
                    g.query_start = None
                    result = TaskBase.__call__(self, *args, **kwargs)
                    logger.bind(
                        queries_amount=g.queries_amount,
                        queries_max_duration=g.queries_max_duration,
                        queries_total_duration=g.queries_total_duration,
                    )
                    return result

        self.Task = _ContextTask  # pylint: disable=invalid-name

    def init_flask_app(self, app: t.Any) -> None:
        self._flask_app = app


celery = MyCelery('psef')  # pylint: disable=invalid-name


def init_app(app: t.Any) -> None:
    """Initialize tasks for the given flask app.

    :param: The flask app to initialize for.
    :returns: Nothing
    """
    celery.conf.update(app.config['CELERY_CONFIG'])
    # This is a weird class that is like a dict but not really.
    celery.conf.update(
        {
            'task_ignore_result': True,
            'celery_hijack_root_logger': False,
            'worker_log_format': '%(message)s',
        }
    )
    celery.init_flask_app(app)


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
    submission_ids: t.Sequence[int], initial: bool = False
) -> None:
    if not submission_ids:  # pragma: no cover
        return

    subs = p.models.Work.query.filter(
        t.cast(p.models.DbColumn[int], p.models.Work.id).in_(
            submission_ids,
        )
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

        file_lookup_tree: t.Dict[int, p.files.FileTree] = {}
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
            parent = os.path.join(tempdir, dir_name)

            if not main_assig:
                old_subs.add(sub.id)
                if archival_arg_present:
                    parent = os.path.join(archive_dir, dir_name)

            os.mkdir(parent)
            part_tree = p.files.restore_directory_structure(sub, parent)
            file_lookup_tree[sub.id] = {
                'name': dir_name,
                'id': -1,
                'entries': [part_tree],
            }

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
                    val = cur + plagiarism_run.submissions_total - tot
                    plagiarism_run.submissions_done = val
                p.models.db.session.commit()
                return True
            return False

        try:
            ok, stdout = p.helpers.call_external(call_args, got_output)
        # pylint: disable=broad-except
        except Exception:  # pragma: no cover
            set_state(p.models.PlagiarismState.crashed)
            raise

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

send_reminder_mails: t.Callable[[
    t.Tuple[int], NamedArg(t.Optional[datetime.datetime], 'eta')
], t.Any] = _send_reminder_mails_1.apply_async  # pylint: disable=invalid-name
