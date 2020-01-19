import os
import html
import uuid
import typing as t
import datetime
import mimetypes

import flask
import werkzeug

from . import api
from .. import auth, files, models, helpers, features
from ..models import db


@api.route('/proxy/<uuid:proxy_id>/<path:path_str>', methods=['GET'])
def get_proxy_file(
    proxy_id: uuid.UUID, path_str: str
) -> werkzeug.wrappers.Response:
    proxy = helpers.get_or_404(
        models.Proxy, proxy_id, also_error=lambda p: p.deleted or p.expired
    )

    path, is_dir = files.split_path(os.path.normpath(path_str))
    if not path or is_dir:
        raise Exception()
    found_file = proxy.get_file(path)
    assert found_file

    ctype, encoding = mimetypes.guess_type(path_str)
    res = flask.Response(found_file.open(), mimetype=ctype)
    res.headers['Content-Security-Policy'] = proxy.csp_header
    return res
