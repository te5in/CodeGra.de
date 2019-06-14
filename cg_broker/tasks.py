import datetime
import typing as t
import uuid

import requests
import structlog
from celery import signals
from sqlalchemy.sql.expression import and_ as sql_and

from cg_celery import CGCelery
from cg_logger import bound_to_logger

from . import BrokerFlask, app, models
from .models import db

celery = CGCelery(__name__, signals)
logger = structlog.get_logger()


def init_app(app: BrokerFlask) -> None:
    celery.init_flask_app(app)


@celery.task
def maybe_start_unassigned_runner() -> None:
    not_divided_jobs = db.session.query(
        models.Job).filter_by(runner=None).with_for_update().all()
    not_assigned_runners = models.Runner.get_active_runners().filter_by(
        job_id=None).with_for_update().all()

    with bound_to_logger(jobs=not_divided_jobs, runners=not_assigned_runners):
        if len(not_divided_jobs) < len(not_assigned_runners):
            logger.error('More runners than jobs active')
            return
        elif len(not_divided_jobs) == len(not_assigned_runners):
            logger.info('No new runners needed')
            return
        else:
            logger.info('More runners are needed')

    if not models.Runner.can_start_more_runners():
        return

    runner = models.Runner.create_of_type(app.config['AUTO_TEST_TYPE'])
    db.session.add(runner)
    db.session.commit()
    _start_runner.delay(runner.id.hex)


@celery.task
def maybe_start_runner_for_job(job_id: int) -> None:
    job = db.session.query(
        models.Job).filter_by(id=job_id).with_for_update().one_or_none()
    if job is None:
        logger.warning('Job to start runner for not found', job_id=job_id)
        return
    elif job.runner is not None:
        logger.warning('Job to start runner already as a runner assigned')
        return

    if not models.Runner.can_start_more_runners():
        return

    runner = models.Runner.create_of_type(app.config['AUTO_TEST_TYPE'])
    runner.job_id = job_id
    db.session.add(runner)
    db.session.commit()
    _start_runner.delay(runner.id.hex)


def _kill_runner(runner: 'models.Runner') -> None:
    assert runner.should_clean

    runner.state = models.RunnerState.cleaning
    db.session.commit()
    runner.cleanup_runner()
    runner.state = models.RunnerState.cleaned
    db.session.commit()

    maybe_start_unassigned_runner.delay()


@celery.task
def _start_runner(runner_hex_id: str) -> None:
    runner_id = uuid.UUID(hex=runner_hex_id)

    runner = db.session.query(
        models.Runner).filter_by(id=runner_id).with_for_update().one_or_none()

    if runner is None:
        logger.info('Cannot find runner')
        return
    elif runner.state != models.RunnerState.not_running:
        logger.info(
            'Runner not in not_running state',
            runner=runner,
            state=runner.state)
        return

    runner.state = models.RunnerState.creating

    try:
        runner.start_runner()
    except:
        logger.error('Failed to start runner', exc_info=True)
        _kill_runner(runner)
        raise
    else:
        db.session.commit()


@celery.task
def cleanup_runner_of_job(job_id: int) -> None:
    runner = db.session.query(models.Runner).filter_by(
        job_id=job_id).with_for_update().one_or_none()

    if runner is None:
        logger.warning('Runner not found')
        return
    elif not runner.should_clean:
        logger.info('Runner already cleaned up')
        return

    _kill_runner(runner)


@celery.task
def add_1(first: int, second: int) -> int:  # pragma: no cover
    """This function is used for testing if celery works. What it actually does
    is completely irrelevant.
    """
    return first + second
