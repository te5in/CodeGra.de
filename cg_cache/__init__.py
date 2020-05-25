import flask

from . import inter_request, intra_request


def init_app(app: flask.Flask) -> None:
    inter_request.init_app(app)
    intra_request.init_app(app)
