"""This module implements the admin panel of our broker.

SPDX-License-Identifier: AGPL-3.0-only
"""
import uuid
import typing as t
import secrets

import structlog
from flask import (
    Blueprint, abort, flash, request, session, url_for, redirect,
    render_template
)
from flask_login import (
    UserMixin, LoginManager, login_user, logout_user, login_required
)
from werkzeug.wrappers import Response

from cg_sqlalchemy_helpers.types import DbColumn

from . import BrokerFlask, app, tasks, models
from .models import db

logger = structlog.get_logger()

login_manager = LoginManager()  # pylint: disable=invalid-name

admin = Blueprint("admin", __name__)  # pylint: disable=invalid-name


def init_app(flask_app: BrokerFlask) -> None:
    """Add the admin panel blueprint to the given ``flask_app``.
    """
    flask_app.register_blueprint(admin, url_prefix="/admin/")
    login_manager.init_app(flask_app)


@login_manager.unauthorized_handler
def unauthorized_request() -> Response:
    """This function is called if a unauthorized user requests a route which is
    protected.
    """
    logger.warning(
        'User tried to access restricted page without password',
        requested_url=request.url
    )
    return redirect(url_for('.login', next_url=request.url))


@admin.add_app_template_global
def csrf_token() -> str:
    """Get the csrf_token of this session, and generate one if it is not
    available.
    """
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_urlsafe(64)
    return session['_csrf_token']


@admin.before_request
def csrf_protect() -> None:
    """Protect the current route by checking if the ``_csrf_token`` is correct.
    """
    if request.method in {'POST', 'DELETE'}:
        token = session.pop('_csrf_token', None)
        got = request.form.get('_csrf_token')
        if token is None or token != got:
            logger.error('CSRF was not correct', got=got, expected=token)
            abort(403)


class AdminUser(UserMixin):  # type: ignore
    """The only valid user of the admin panel: the admin user!
    """

    @staticmethod
    def get_id() -> str:
        return '1'


@login_manager.user_loader
def load_user(user_id: str) -> t.Optional[UserMixin]:
    """Load the user with the given ``user_id``.
    """
    admin_user = AdminUser()
    if user_id == admin_user.get_id():
        return admin_user
    return None


@admin.route('/logout', methods=['POST'])
def logout() -> Response:
    """Logout the current user by clearing the session.
    """
    logout_user()
    flash('You were logged out successfully')
    return redirect(url_for('.login'))


@admin.route('/login', methods=['GET', 'POST'])
def login() -> Response:
    """Login to the admin panel, or get the admin panel page.
    """
    if request.method == 'GET':
        return render_template('login.j2', runners=[])
    elif request.method == 'POST':
        next_url = request.args.get('next', url_for('.show_all_runners'))
        if secrets.compare_digest(
            request.form['password'], app.config['ADMIN_PASSWORD']
        ):
            login_user(AdminUser())
            return redirect(next_url)
        else:
            flash('Password is wrong!')
            logger.error(
                'User tried to login to broker admin panel with wrong password'
            )
            return redirect(
                url_for('.login', next=request.args.get('next', None))
            )
    else:
        raise RuntimeError


@admin.route('/runners/', methods=['GET'])
@login_required
def show_all_runners() -> Response:
    """Get all runners in a nice (?) layout.
    """
    runners = db.session.query(models.Runner).order_by(
        t.cast(DbColumn, models.Runner.created_at).desc()
    ).all()
    return render_template('runners.j2', runners=runners)


@admin.route('/jobs/', methods=['GET'])
@login_required
def show_all_jobs() -> Response:
    """Get all jobs in a nice (?) layout.
    """
    jobs = db.session.query(models.Job).order_by(
        t.cast(DbColumn, models.Job.created_at).desc()
    ).all()
    return render_template('jobs.j2', jobs=jobs)


@admin.route('/runners/<runner_hex_id>/stop', methods=['POST'])
@login_required
def stop_runner(runner_hex_id: str) -> Response:
    """Stop the given runner.

    .. note::

        The runner will not be stopped immediately, as this is done in a celery
        task.
    """
    runner_id = uuid.UUID(hex=runner_hex_id)
    runner = db.session.query(models.Runner).get(runner_id)
    assert runner is not None

    tasks.kill_runner.delay(runner.id.hex)
    flash('Stopping runner')

    return redirect(url_for('.show_all_runners'))


@admin.route('/runners/', methods=['POST'])
@login_required
def create_runner() -> Response:
    """Create a new unsigned runner.
    """
    if not models.Runner.can_start_more_runners():
        flash('We cannot create more runners, as the maximum is reached')
    else:
        try:
            amount = int(request.form.get('amount') or '1')
        except (KeyError, ValueError):
            flash('Amount is not a number')
        else:
            flash(f'Starting {amount} runners')
            tasks.start_unassigned_runner.delay(amount)

    return redirect(url_for('.show_all_runners'))
