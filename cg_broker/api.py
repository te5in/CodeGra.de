import secrets
import time
import typing as t
from datetime import datetime
from functools import wraps
from uuid import UUID

import structlog
from flask import Blueprint, g, make_response, request
from flask_expects_json import expects_json
from sqlalchemy.sql.expression import and_ as sql_and

from cg_json import JSONResponse, jsonify
from cg_sqlalchemy_helpers.types import DbColumn

from . import BrokerFlask, app, models, tasks, utils
from .exceptions import BadRequest, NotFoundException, PermissionException
from .models import db

logger = structlog.get_logger()

api = Blueprint("api", __name__)  # pylint: disable=invalid-name
EmptyResponse = t.NewType('EmptyResponse', object)
T_CAL = t.TypeVar('T_CAL', bound=t.Callable)


def init_app(app: BrokerFlask) -> None:
    app.register_blueprint(api, url_prefix="/api/v1")


def make_empty_response() -> EmptyResponse:
    """Create an empty response.

    :returns: A empty response with status code 204
    """
    response = make_response('')
    response.status_code = 204

    return EmptyResponse(response)


def instance_route(f: T_CAL) -> T_CAL:
    @wraps(f)
    def __inner(*args: object, **kwargs: object) -> t.Any:
        password = request.headers['CG-Broker-Pass']
        instance_name = request.headers['CG-Broker-Instance']

        try:
            if not secrets.compare_digest(app.allowed_instances[instance_name],
                                          password):
                raise PermissionException(401)
        except (KeyError, TypeError):
            raise PermissionException(401)

        return f(*args, **kwargs)

    return t.cast(T_CAL, __inner)


@api.route('/jobs/', methods=['POST'])
@expects_json({
    'type': 'object',
    'properties': {
        'job_id': {
            'type': 'string',
        },
    },
    "additionalProperties": False,
    "minProperties": 1,
})
@instance_route
def register_job() -> EmptyResponse:
    job = models.Job(
        remote_id=g.data['job_id'],
        cg_url=request.headers['CG-Broker-Instance'])
    db.session.add(job)
    db.session.commit()

    assert job.id is not None
    tasks.maybe_start_runner_for_job.delay(job.id)

    return make_empty_response()


@api.route('/jobs/<job_id>', methods=['DELETE'])
@instance_route
def delete_job(job_id: str) -> EmptyResponse:
    job = db.session.query(models.Job).filter_by(
        remote_id=job_id).with_for_update().one_or_none()
    if job is None:
        # Make sure job will never be able to run
        job = models.Job(
            cg_url=request.headers['CG-Broker-Instance'], remote_id=job_id)
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
    'properties': {
        'runner_ip': {
            'type': 'string',
        },
    },
    "additionalProperties": False,
    "minProperties": 1,
})
@instance_route
def register_runner_for_job(job_id: str) -> EmptyResponse:
    job = db.session.query(models.Job).filter_by(
        remote_id=job_id).with_for_update().one_or_none()
    if job is None:
        logger.info('Job not found!', job_id=job_id)
        raise NotFoundException
    elif job.state == models.JobState.finished:
        raise PermissionException(403)

    logger.info('Searching for runner', runner_ipaddr=g.data['runner_ip'])

    runner = db.session.query(models.Runner).filter_by(
        ipaddr=g.data['runner_ip'],
        state=models.RunnerState.creating,
        job_id=job.id,
    ).with_for_update().one_or_none()

    # Job does not have a reserved runner, maybe a unreserved runner is
    # available.
    if runner is None:
        runner = db.session.query(models.Runner).filter_by(
            ipaddr=g.data['runner_ip'],
            state=models.RunnerState.creating,
            job_id=None,
        ).with_for_update().one_or_none()

        # No unreserved runner available either
        if runner is None:
            logger.info(
                'Runner with given ip not found', ipaddr=g.data['runner_ip'])
            raise NotFoundException

    logger.info('Found runner', runner_id=runner.id)

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
            'items': {
                'type': 'object',
            },
        },
    },
    "additionalProperties": False,
    "minProperties": 1,
})
def emit_log_for_runner() -> EmptyResponse:
    runner = db.session.query(models.Runner).filter(
        models.Runner.ipaddr == request.remote_addr,
        ~models.Runner.last_log_emitted,
        sql_and(models.Runner.state != models.RunnerState.cleaning,
                models.Runner.state != models.RunnerState.cleaned),
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
        log['original_timestamp'] = log['timestamp']
        log['from_tester'] = True
        log['main_job_id'] = main_job_id
        log['runner_state'] = runner_state
        log['__level__'] = log['level']
        log['original_event'] = log.pop('event')
        logger.info('Got log from runner', **log)

    return make_empty_response()
