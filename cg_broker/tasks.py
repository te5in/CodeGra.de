import datetime
import typing as t
import uuid

import requests
import structlog
from celery import signals
from sqlalchemy.sql.expression import and_ as sql_and

from cg_celery import CGCelery

from . import BrokerFlask, app, models
from .models import db

celery = CGCelery(__name__, signals)
logger = structlog.get_logger()
logger.error('hello')


def init_app(app: BrokerFlask) -> None:
    celery.init_flask_app(app)


@celery.task
def maybe_start_runner_for_job(job_id: int) -> None:
    # We do a all and len here as count() and with_for_update cannot be used in
    # combination.
    amount = len(models.Runner.get_active_runners().with_for_update().all())
    if amount >= app.config['MAX_AMOUNT_OF_RUNNERS']:
        logger.warning('Too many runners active', active_amount=amount)
        return

    typ = models.Runner.__mapper__.polymorphic_map[
        app.config['AUTO_TEST_TYPE']].class_
    runner = typ.create()
    runner.job_id = job_id
    if runner is not None:
        db.session.add(runner)
        db.session.commit()
        _start_runner.delay(runner.id.hex)


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
    db.session.commit()

    try:
        runner.start_runner()
    except:
        logger.error('Failed to start runner')
        runner.state = models.RunnerState.cleaning
        db.session.commit()
        runner.cleanup_runner()
        runner.state = models.RunnerState.cleaned
        db.session.commit()
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

    runner.state = models.RunnerState.cleaning
    db.session.commit()

    runner.cleanup_runner()

    runner.state = models.RunnerState.cleaned
    db.session.commit()


@celery.task
def add_1(first: int, second: int) -> int:  # pragma: no cover
    """This function is used for testing if celery works. What it actually does
    is completely irrelevant.
    """
    return first + second
