import flask
import pytest

import cg_cache.intra_request as c


def pytest_addoption(parser):
    try:
        parser.addoption(
            "--postgresql",
            action="store",
            default=False,
            help="Run the test using postresql"
        )
    except ValueError:
        pass


@pytest.fixture(scope='session')
def app():
    app = flask.Flask(__name__)
    c.init_app(app)
    yield app
