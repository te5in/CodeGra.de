"""This file defines all celery tasks for the broker.

SPDX-License-Identifier: AGPL-3.0-only
"""
import uuid
import typing as t
import datetime

import structlog
from celery import signals
from sqlalchemy.sql.expression import and_
from sqlalchemy.sql.expression import func as sql_func

from cg_celery import CGCelery
from cg_logger import bound_to_logger
from cg_sqlalchemy_helpers.types import DbColumn

from . import BrokerFlask, app, models
from .models import db

celery = CGCelery(__name__, signals)  # pylint: disable=invalid-name
logger = structlog.get_logger()


def init_app(flask_app: BrokerFlask) -> None:
    celery.init_flask_app(flask_app)


@celery.task(acks_late=True, max_retries=10, reject_on_worker_lost=True)
def maybe_kill_unneeded_runner(runner_hex_id: str) -> None:
    """Maybe kill the given runner if it is still unassigned.

    :param runner_hex_id: The hex id of the runner to maybe kill.
    """
    # TODO: If a runner goes from unassigned, to assigned, to unassigned we
    # might kill it too soon. As we start a job to kill it for the first time
    # it is unassigned, and this job might be executed while it is unassigned
    # for the second time.
    runner_id = uuid.UUID(hex=runner_hex_id)
    runner = db.session.query(
        models.Runner
    ).filter_by(id=runner_id).with_for_update().one_or_none()

    with bound_to_logger(runner=runner):
        if runner is None:
            logger.warning('Runner was deleted')
            return
        elif not runner.is_before_run:
            logger.info(
                'Runner has already finished running',
                runner_state=runner.state
            )
            return
        elif runner.job_id is not None:
            logger.info('Runner is needed', job_of_runner=runner.job_id)
            return

        logger.error('Runner is still not doing anything')
        runner.kill(maybe_start_new=False)


@celery.task
def maybe_start_unassigned_runner() -> None:
    """Start an unassigned runner if we have jobs that need a runner.
    """
    # Do not use count so we can lock all these runners, this makes sure we
    # will not create new runners while we are counting.
    active_runners = models.Runner.get_all_active_runners()
    not_assigned_runners = len(
        active_runners.filter_by(job_id=None).with_for_update().all()
    )

    sql = db.session.query(
        t.cast(DbColumn[int], models.Job._wanted_runners),  # pylint: disable=protected-access
        t.cast(t.Type[int], sql_func.count(models.Runner.id))
    ).filter(
        models.Job._state != models.JobState.finished,  # pylint: disable=protected-access
    ).join(
        models.Runner,
        and_(
            models.Runner.job_id == models.Job.id,
            t.cast(DbColumn[models.RunnerState], models.Runner.state).in_(
                models.RunnerState.get_active_states()
            )
        ),
        isouter=True
    ).group_by(models.Job.id)
    needed_runners = sum(max(0, wanted - has) for wanted, has in sql)

    with bound_to_logger(
        needed_runners=needed_runners,
        unassigned_runners=not_assigned_runners,
    ):
        if needed_runners < not_assigned_runners:
            logger.error('More runners than jobs active')
        elif needed_runners == not_assigned_runners:
            logger.info('No new runners needed')
        else:
            logger.info('More runners are needed')
            start_unassigned_runner(needed_runners)


@celery.task
def start_unassigned_runner(amount: int = 1) -> None:
    """Unconditionally start an unassigned runner.

    A unassigned runner is a runner which is not linked to one job.
    """
    to_start = []
    for _ in range(amount):
        if not models.Runner.can_start_more_runners():
            return

        runner = models.Runner.create_of_type(app.config['AUTO_TEST_TYPE'])
        db.session.add(runner)
        to_start.append(runner)

    db.session.commit()

    for runner in to_start:
        _start_runner.delay(runner.id.hex)


@celery.task
def maybe_start_runners_for_job(job_id: int) -> None:
    """Maybe start a runner assigned to the given ``job_id``.

    The runner is only started when the job doesn't already have a runner and
    there are not too many runners active.
    """
    job = db.session.query(
        models.Job
    ).filter_by(id=job_id).with_for_update().one_or_none()

    if job is None:
        logger.warning('Job to start runner for not found', job_id=job_id)
        return

    active_runners = models.Runner.get_all_active_runners().filter_by(
        job_id=job.id
    ).all()
    still_needed = job.wanted_runners - len(active_runners)

    if still_needed <= 0:
        logger.warning('Job to already has enough runners assigned')
        return

    unassigned_runners = db.session.query(models.Runner).filter(
        t.cast(DbColumn[models.RunnerState], models.Runner.state).in_(
            models.RunnerState.get_before_running_states()
        ),
        t.cast(DbColumn[t.Optional[int]], models.Runner.job_id).is_(None)
    ).with_for_update().limit(still_needed).all()

    to_start = []

    for _ in range(still_needed):
        if unassigned_runners:
            # Aha, we are lucky, we have an unassigned runner. Lets assign it
            # :)
            unassigned_runners.pop().job = job
        elif not models.Runner.can_start_more_runners():
            break
        else:
            runner = models.Runner.create_of_type(app.config['AUTO_TEST_TYPE'])
            runner.job_id = job_id
            db.session.add(runner)
            to_start.append(runner)

    db.session.commit()

    for runner in to_start:
        _start_runner.delay(runner.id.hex)


@celery.task
def kill_runner(runner_hex_id: str) -> None:
    """Kill the runner with the given ``runner_hex_id``.
    """
    runner_id = uuid.UUID(hex=runner_hex_id)
    runner = db.session.query(
        models.Runner
    ).filter_by(id=runner_id).with_for_update().one_or_none()
    if runner is None:
        logger.warning('Runner not found')
        return
    elif not runner.should_clean:
        logger.info('Runner already cleaned up')
        return

    runner.kill(maybe_start_new=True)


@celery.task
def _start_runner(runner_hex_id: str) -> None:
    runner_id = uuid.UUID(hex=runner_hex_id)
    runner = db.session.query(
        models.Runner
    ).filter_by(id=runner_id).with_for_update().one_or_none()

    if runner is None:
        logger.info('Cannot find runner')
        return
    elif runner.state != models.RunnerState.not_running:
        logger.info(
            'Runner not in not_running state',
            runner=runner,
            state=runner.state
        )
        return

    maybe_kill_unneeded_runner.apply_async(
        (runner.id.hex, ),
        eta=datetime.datetime.utcnow() +
        datetime.timedelta(minutes=app.config['RUNNER_MAX_TIME_ALIVE'])
    )

    runner.state = models.RunnerState.creating

    try:
        runner.start_runner()
    except:
        logger.error('Failed to start runner', exc_info=True)
        # The kill method commits
        runner.kill(maybe_start_new=True)
        raise
    else:
        db.session.commit()


@celery.task
def cleanup_runners_of_job(job_id: int) -> None:
    """Cleanup the runners of the given job.
    """
    runners = db.session.query(
        models.Runner
    ).filter_by(job_id=job_id).with_for_update().all()

    to_clean = []
    for runner in runners:
        if runner.should_clean:
            runner.state = models.RunnerState.cleaning
            to_clean.append(runner)
        else:
            logger.info('Runner already cleaned up')

    db.session.commit()

    for runner in to_clean:
        runner.kill(maybe_start_new=True)


@celery.task
def add_1(first: int, second: int) -> int:  # pragma: no cover
    """This function is used for testing if celery works. What it actually does
    is completely irrelevant.
    """
    return first + second
