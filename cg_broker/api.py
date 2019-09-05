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
from sqlalchemy.sql.expression import func as sql_func

from cg_flask_helpers import callback_after_this_request
from cg_sqlalchemy_helpers.types import DbColumn

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


@api.route('/jobs/', methods=['POST', 'PUT'])
@expects_json({
    'type': 'object',
    'properties': {
        'job_id': {'type': 'string'},
        'wanted_runners': {'type': 'integer'},
        'metadata': {'type': 'object'},
    },
    'required': ['job_id'],
})
@instance_route
def register_job() -> EmptyResponse:
    """Register a new job.

    If needed a runner will be started for this job.
    """
    remote_job_id = g.data['job_id']
    cg_url = request.headers['CG-Broker-Instance']
    job = None

    if request.method == 'PUT':
        job = db.session.query(models.Job).filter_by(
            remote_id=remote_job_id,
            cg_url=cg_url,
        ).one_or_none()

    if job is None:
        job = models.Job(
            remote_id=remote_job_id,
            cg_url=cg_url,
        )
        db.session.add(job)

    job.update_metadata(g.data.get('metadata', {}))
    job.wanted_runners = g.data.get('wanted_runners', 1)
    active_runners = models.Runner.get_all_active_runners().filter_by(
        job_id=job.id
    ).with_for_update().all()

    too_many = len(active_runners) - job.wanted_runners
    logger.info(
        'Job was updated',
        wanted_runners=job.wanted_runners,
        amount_active=len(active_runners),
        too_many=too_many,
        metadata=job.job_metadata,
    )

    for runner in active_runners:
        if too_many <= 0:
            break

        if runner.state in models.RunnerState.get_before_running_states():
            runner.make_unassigned()
            too_many -= 1

    db.session.commit()

    job_id = job.id
    callback_after_this_request(
        lambda: tasks.maybe_start_runners_for_job.delay(job_id)
    )
    assert job.id is not None

    return make_empty_response()


@api.route('/jobs/<job_id>/runners/', methods=['DELETE'])
@expects_json({
    'type': 'object',
    'properties': {'ipaddr': {'type': 'string'}, },
    'required': ['ipaddr'],
})
@instance_route
def remove_runner_of_job(job_id: str) -> EmptyResponse:
    """Remove (kill) a runner of the given job.

    The runner is given by its ip in the data of the DELETE request.
    """
    job = db.session.query(
        models.Job
    ).filter_by(remote_id=job_id).with_for_update().one_or_none()
    if job is None:
        raise NotFoundException

    runner = db.session.query(models.Runner).filter_by(
        ipaddr=g.data['ipaddr'], job=job
    ).filter(
        t.cast(DbColumn[models.RunnerState], models.Runner.state).in_(
            models.RunnerState.get_active_states()
        )
    ).with_for_update().one_or_none()
    if runner is None:
        raise NotFoundException

    runner.job_id = None
    db.session.commit()

    tasks.kill_runner(runner.id.hex)
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

    runners = db.session.query(models.Runner).filter_by(
        job_id=job.id,
    ).with_for_update().all()
    job.state = models.JobState.finished
    job.wanted_runners = 0
    for runner in runners:
        if runner.state in models.RunnerState.get_before_running_states():
            runner.make_unassigned()

    db.session.commit()

    tasks.cleanup_runners_of_job.delay(job.id)

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
    runner_ip = g.data['runner_ip']
    job = db.session.query(
        models.Job
    ).filter_by(remote_id=job_id).with_for_update().one_or_none()
    if job is None:
        logger.info('Job not found!', job_id=job_id)
        raise NotFoundException

    logger.info(
        'Searching for runner',
        runner_ipaddr=g.data['runner_ip'],
        job_id=job.id
    )

    # We do an extra query here to make sure we lock these runners.
    active_job_runners = models.Runner.get_all_active_runners().filter_by(
        job_id=job.id
    ).with_for_update().all()
    runner = next((r for r in active_job_runners if r.ipaddr == runner_ip),
                  None)

    # Job does not have a reserved runner, maybe a unreserved runner is
    # available.
    if runner is None:
        amount_running = sum(
            1 for r in active_job_runners
            if r.state == models.RunnerState.running
        )
        if amount_running >= job.wanted_runners:
            logger.info('Job already has enough runners running')
            raise NotFoundException

        logger.info(
            'No runner found in the assigned runners, finding unassigned'
            ' runner'
        )

        # This job already has an assigned runner. It is fine to use
        # another runner (which might present itself sooner to the
        # CodeGrade instance, so using it will only simply improve
        # latency).
        runner = db.session.query(models.Runner).filter_by(
            ipaddr=runner_ip,
            state=models.RunnerState.creating,
            job_id=None,
        ).with_for_update().first()

    if runner is None:
        logger.info('No runner found unassigned, trying to steal')
        # Try to find a runner of a job which has more than one runner
        # assigned to it.
        runner = db.session.query(models.Runner).filter(
            models.Runner.ipaddr == runner_ip,
            t.cast(DbColumn[models.RunnerState], models.Runner.state).in_(
                models.RunnerState.get_before_running_states()
            ),
            t.cast(DbColumn[int], models.Runner.job_id).in_(
                db.session.query(t.cast(DbColumn[int], models.Job.id)).join(
                    models.Runner,
                    sql_and(
                        models.Runner.job_id == models.Job.id,
                        t.cast(
                            DbColumn[models.RunnerState], models.Runner.state
                        ).in_(models.RunnerState.get_active_states())
                    )
                ).having(
                    sql_func.count(models.Runner.id) > 1,
                ).group_by(models.Job.id)
            )
        ).with_for_update().first()

    # No runner available
    if runner is None:
        logger.info(
            'Runner with given ip not found', ipaddr=g.data['runner_ip']
        )
        raise NotFoundException

    before_start_job = [
        r for r in active_job_runners if r.id != runner.id and
        r.state in models.RunnerState.get_before_running_states()
    ]
    if runner.job_id != job.id:
        active_job_runners.append(runner)

    if before_start_job and len(active_job_runners) > job.wanted_runners:
        logger.info('Making one of the assigned runners unassigned')
        before_start_job[0].make_unassigned()

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
