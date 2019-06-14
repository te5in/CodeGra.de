import os
import typing as t
from configparser import ConfigParser
from datetime import timedelta

import flask
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from mypy_extensions import TypedDict

import cg_logger

if t.TYPE_CHECKING:
    from . import models

BrokerConfig = TypedDict(
    'BrokerConfig', {
        'DEBUG': bool,
        'SQLALCHEMY_TRACK_MODIFICATIONS': bool,
        'SQLALCHEMY_DATABASE_URI': str,
        'AUTO_TEST_TYPE': 'models.RunnerType',
        'AWS_INSTANCE_TYPE': str,
        'MAX_AMOUNT_OF_RUNNERS': int,
        'CELERY_CONFIG': t.Dict,
        'RUNNER_MAX_TIME_ALIVE': int,
        '_TRANSIP_USERNAME': str,
        '_TRANSIP_PRIVATE_KEY_FILE': str
    })


class BrokerFlask(flask.Flask):
    config: BrokerConfig  # type: ignore

    def __init__(self, name: str) -> None:
        super().__init__(name)

        def make_parser(case_sensitive: bool) -> ConfigParser:
            delimiters = ('=', )
            if case_sensitive:
                parser = ConfigParser(delimiters=delimiters)
                parser.optionxform = str  # type: ignore
            else:
                parser = ConfigParser(os.environ, delimiters=delimiters)

            config_file = os.getenv("BROKER_CONFIG_FILE", "broker_config.ini")
            parser.read(config_file)
            for req_cat in ['Testers', 'General', 'Instances']:
                if req_cat not in parser:
                    parser[req_cat] = {}
            return parser

        _parser = make_parser(False)

        self.heartbeat_interval = _parser['Testers'].getint(
            'INTERVAL', fallback=15)
        self.heartbeat_max_missed = _parser['Testers'].getint(
            'MAX_MISSED', fallback=5)
        self.auto_test_max_duration = timedelta(
            minutes=int(_parser['Testers'].get('MAX_DURATION', str(24 * 60))))

        self.config['DEBUG'] = _parser['General'].getboolean(
            'DEBUG', fallback=False)
        self.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        self.config['SQLALCHEMY_DATABASE_URI'] = _parser['General'].get(
            'SQLALCHEMY_DATABASE_URI', 'postgresql:///codegrade_broker_dev')

        if self.debug:
            self.config['AUTO_TEST_TYPE'] = models.RunnerType.dev_runner
        else:
            self.config['AUTO_TEST_TYPE'] = models.RunnerType[
                _parser['General'].get('RUNNER_TYPE', 'aws')]

        self.config['AWS_INSTANCE_TYPE'] = _parser['General'].get(
            'AWS_INSTANCE_TYPE', 't3.medium')

        self.config['MAX_AMOUNT_OF_RUNNERS'] = _parser['General'].getint(
            'MAX_AMOUNT_OF_RUNNERS', fallback=1)

        self.config['RUNNER_MAX_TIME_ALIVE'] = _parser['General'].getint(
            'RUNNER_MAX_TIME_ALIVE', fallback=60)

        self.config['_TRANSIP_USERNAME'] = _parser['General'].get(
            'TRANSIP_USERNAME', '')
        self.config['_TRANSIP_PRIVATE_KEY_FILE'] = _parser['General'].get(
            'TRANSIP_PRIVATE_KEY_FILE', '')

        # Convert parser to case sensitve
        _parser = make_parser(True)
        self.config['CELERY_CONFIG'] = dict(_parser['Celery'])

        self.allowed_instances: t.Dict[str, str] = dict(
            _parser['Instances'].items())


if t.TYPE_CHECKING:
    app: 'BrokerFlask'
else:
    from flask import current_app as app


def create_app() -> flask.Flask:
    from . import api, exceptions, models, tasks

    app = BrokerFlask(__name__)
    cg_logger.init_app(app, set_user=False)
    models.init_app(app)
    api.init_app(app)
    tasks.init_app(app)
    exceptions.init_app(app)

    admin = Admin(app, name='microblog', template_mode='bootstrap3')
    admin.add_view(ModelView(models.Job, models.db.session))
    admin.add_view(ModelView(models.Runner, models.db.session))

    if app.debug:
        tasks.add_1.delay(1, 2)

    return app
