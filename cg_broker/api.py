"""This module implements the API that is used by all CodeGrade instances.

.. note:: This API is not public in anyway!

SPDX-License-Identifier: AGPL-3.0-only
"""
import typing as t
import secrets
from datetime import datetime
from functools import wraps

import structlog
from flask import Blueprint, g, request, make_response
from flask_expects_json import expects_json
from sqlalchemy.sql.expression import and_ as sql_and

from . import BrokerFlask, app, tasks, models
from .models import db
from .exceptions import NotFoundException, PermissionException

logger = structlog.get_logger()

api = Blueprint("api", __name__)  # pylint: disable=invalid-name
EmptyResponse = t.NewType('EmptyResponse', object)
T_CAL = t.TypeVar('T_CAL', bound=t.Callable)  # pylint: disable=invalid-name


def init_app(flask_app: BrokerFlask) -> None:
    flask_app.register_blueprint(api, url_prefix="/api/v1")


def make_empty_response() -> EmptyResponse:
    """Create an empty response.

    :returns: A empty response with status code 204
    """
    response = make_response('')
    response.status_code = 204

    return EmptyResponse(response)


def instance_route(f: T_CAL) -> T_CAL:
    """This function is a decorator that makes sure that the given fuction can
    only be used when the correct headers are included.

    This effectively adds some form of authentication to the routes.
    """

    @wraps(f)
    def __inner(*args: object, **kwargs: object) -> t.Any:
        password = request.headers['CG-Broker-Pass']
        instance_name = request.headers['CG-Broker-Instance']

        try:
            if not secrets.compare_digest(
                app.allowed_instances[instance_name], password
            ):
                raise PermissionException(401)
        except (KeyError, TypeError):
            raise PermissionException(401)

        return f(*args, **kwargs)

    return t.cast(T_CAL, __inner)


@api.route('/jobs/', methods=['POST'])
@expects_json({
    'type': 'object',
    'properties': {'job_id': {'type': 'string', }, },
    "additionalProperties": False,
    "minProperties": 1,
})
@instance_route
def register_job() -> EmptyResponse:
    """Register a new job.

    If needed a runner will be started for this job.
    """
    job = models.Job(
        remote_id=g.data['job_id'],
        cg_url=request.headers['CG-Broker-Instance']
    )
    db.session.add(job)
    db.session.commit()

    assert job.id is not None
    tasks.maybe_start_runner_for_job.delay(job.id)

    return make_empty_response()


@api.route('/jobs/<job_id>', methods=['DELETE'])
@instance_route
def delete_job(job_id: str) -> EmptyResponse:
    """Delete the given job.

    If this job had any runners associated with it these will be stopped and
    cleaned.
    """
    job = db.session.query(
        models.Job
    ).filter_by(remote_id=job_id).with_for_update().one_or_none()
    if job is None:
        # Make sure job will never be able to run
        job = models.Job(
            cg_url=request.headers['CG-Broker-Instance'], remote_id=job_id
        )
        job.state = models.JobState.finished
        db.session.add(job)
        db.session.commit()
        return make_empty_response()
    elif job.state == models.JobState.finished:
        logger.info('Job already cleaned')
        return make_empty_response()

    job.state = models.JobState.finished
    db.session.commit()

    tasks.cleanup_runner_of_job.delay(job.id)

    return make_empty_response()


@api.route('/jobs/<job_id>/runners/', methods=['POST'])
@expects_json({
    'type': 'object',
    'properties': {'runner_ip': {'type': 'string'}},
    "additionalProperties": False,
    "minProperties": 1,
})
@instance_route
def register_runner_for_job(job_id: str) -> EmptyResponse:
    """Check if the given ``runner_ip`` is allowed to be used for the given
    job (identified by ``job_id``).
    """
    job = db.session.query(
        models.Job
    ).filter_by(remote_id=job_id).with_for_update().one_or_none()
    if job is None:
        logger.info('Job not found!', job_id=job_id)
        raise NotFoundException
    elif job.state != models.JobState.waiting_for_runner:
        # Make sure we don't assign a job two runners.
        raise PermissionException(403)

    logger.info(
        'Searching for runner',
        runner_ipaddr=g.data['runner_ip'],
        job_id=job.id
    )

    runner = db.session.query(models.Runner).filter_by(
        ipaddr=g.data['runner_ip'],
        state=models.RunnerState.creating,
        job_id=job.id,
    ).with_for_update().one_or_none()

    # Job does not have a reserved runner, maybe a unreserved runner is
    # available.
    if runner is None:
        # This job already has an assigned runner. It is fine to use
        # another runner (which might present itself sooner to the
        # CodeGrade instance, so using it will only simply improve
        # latency). However, this is only OK if this job does not already
        # have a confirmed runner, so the state should be lower than
        # ``started``.
        runner = db.session.query(models.Runner).filter_by(
            ipaddr=g.data['runner_ip'],
            state=models.RunnerState.creating,
            job_id=None,
        ).with_for_update().first()

        # No unreserved runner available either
        if runner is None:
            logger.info(
                'Runner with given ip not found', ipaddr=g.data['runner_ip']
            )
            raise NotFoundException

    logger.info(
        'Found runner',
        runner_id=runner.id,
        time_since_runner_start=(datetime.utcnow() -
                                 runner.created_at).total_seconds()
    )
    runner.state = models.RunnerState.running
    job.state = models.JobState.started
    runner.job = job
    db.session.commit()
    return make_empty_response()


@api.route('/logs/', methods=['POST'])
@expects_json({
    'type': 'object',
    'properties': {
        'logs': {
            'type': 'array',
            'items': {'type': 'object', },
        },
    },
    "additionalProperties": False,
    "minProperties": 1,
})
def emit_log_for_runner() -> EmptyResponse:
    """Emit log lines for a runner.
    """
    runner = db.session.query(models.Runner).filter(
        models.Runner.ipaddr == request.remote_addr,
        ~models.Runner.last_log_emitted,
        sql_and(
            models.Runner.state != models.RunnerState.cleaning,
            models.Runner.state != models.RunnerState.cleaned
        ),
    ).with_for_update().one_or_none()
    if runner is None:
        raise NotFoundException

    if runner.state == models.RunnerState.running:
        runner.last_log_emitted = True
    db.session.commit()

    runner_state = runner.state.name
    main_job_id = runner.job_id
    del runner

    for log in g.data['logs']:
        assert 'level' in log
        getattr(logger, log['level'], logger.info)(
            **log,
            from_tester=True,
            original_timestamp=log['timestamp'],
            main_job_id=main_job_id,
            runner_state=runner_state,
        )

    return make_empty_response()
