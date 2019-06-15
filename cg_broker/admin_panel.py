import secrets
import typing as t
import uuid

import structlog
from flask import (Blueprint, abort, flash, redirect, render_template, request,
                   session, url_for)
from flask_login import (LoginManager, UserMixin, current_user, login_required,
                         login_user, logout_user)
from werkzeug.wrappers import Response

from cg_sqlalchemy_helpers.types import DbColumn

from . import BrokerFlask, app, models, tasks
from .models import db

logger = structlog.get_logger()

login_manager = LoginManager()

admin = Blueprint("admin", __name__)  # pylint: disable=invalid-name


def init_app(app: BrokerFlask) -> None:
    app.register_blueprint(admin, url_prefix="/admin/")
    login_manager.init_app(app)
    login_manager.login_view = '.login'


@admin.add_app_template_global
def csrf_token() -> str:
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_urlsafe(64)
    return session['_csrf_token']


@admin.before_request
def csrf_protect() -> None:
    if request.method in {'POST', 'DELETE'}:
        token = session.pop('_csrf_token', None)
        got = request.form.get('_csrf_token')
        if token is None or token != got:
            logger.error('CSRF was not correct', got=got, expected=token)
            abort(403)


class AdminUser(UserMixin):  # type: ignore
    def get_id(self) -> str:
        return '1'


@login_manager.user_loader
def load_user(user_id: str) -> t.Optional[UserMixin]:
    admin_user = AdminUser()
    if user_id == admin_user.get_id():
        return admin_user
    return None


@admin.route('/logout', methods=['POST'])
def logout() -> Response:
    logout_user()
    flash('You were logged out successfully')
    return redirect(url_for('.login'))


@admin.route('/login', methods=['GET', 'POST'])
def login() -> Response:
    if request.method == 'GET':
        return render_template('login.j2', runners=[])
    elif request.method == 'POST':
        next_url = request.args.get('next', url_for('.show_all_runners'))
        if secrets.compare_digest(request.form['password'],
                                  app.config['ADMIN_PASSWORD']):
            login_user(AdminUser())
            return redirect(next_url)
        else:
            flash('Password is wrong!')
            logger.error(
                'User tried to login to broker admin panel with wrong password'
            )
            return redirect(
                url_for('.login', next=request.args.get('next', None)))
    else:
        assert False


@admin.route('/runners/', methods=['GET'])
@login_required
def show_all_runners() -> Response:
    runners = db.session.query(models.Runner).order_by(
        t.cast(DbColumn, models.Runner.created_at).desc()).all()
    return render_template('runners.j2', runners=runners)


@admin.route('/jobs/', methods=['GET'])
@login_required
def show_all_jobs() -> Response:
    jobs = db.session.query(models.Job).order_by(
        t.cast(DbColumn, models.Job.created_at).desc()).all()
    return render_template('jobs.j2', jobs=jobs)


@admin.route('/runners/<runner_hex_id>/stop', methods=['POST'])
@login_required
def stop_runner(runner_hex_id: str) -> Response:
    runner_id = uuid.UUID(hex=runner_hex_id)
    runner = db.session.query(models.Runner).get(runner_id)
    assert runner is not None

    tasks.kill_runner.delay(runner.id.hex)
    flash('Stopping runner')

    return redirect(url_for('.show_all_runners'))


@admin.route('/runners/', methods=['POST'])
@login_required
def create_runner() -> Response:
    if not models.Runner.can_start_more_runners():
        flash('We cannot create more runners, as the maximum is reached')
    else:
        flash('Started runner')
        tasks.start_unassigned_runner.delay()

    return redirect(url_for('.show_all_runners'))
