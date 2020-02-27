"""This file contains all routes for proxies.

SPDX-License-Identifier: AGPL-3.0-only
"""
import os
import re
import uuid
import mimetypes

import flask
import werkzeug
import structlog

from . import api
from .. import app, files, models, helpers
from ..exceptions import APICodes, APIException

logger = structlog.get_logger()


@api.route('/proxy/<uuid:proxy_id>/<path:path_str>', methods=['POST'])
def start_proxy(
    proxy_id: uuid.UUID, path_str: str
) -> werkzeug.wrappers.Response:
    proxy = helpers.get_or_404(
        models.Proxy, proxy_id, also_error=lambda p: p.deleted
    )
    flask.session['proxy_id'] = str(proxy.id)
    return flask.redirect(
        (
            app.config['EXTERNAL_PROXY_URL'] + '/' + str(proxy.id) + '/' +
            path_str
        ),
        code=303
    )


@api.route('/proxy/', methods=['GET'])
@api.route('/proxy/<path:path_str>', methods=['GET'])
@api.route('/proxy/<uuid:proxy_id>/<path:path_str>', methods=['GET'])
def get_proxy_file(
    proxy_id: uuid.UUID = None, path_str: str = ''
) -> werkzeug.wrappers.Response:
    """Get a file for the given proxy.

    :param proxy_id: The proxy in which you want to get a file.
    :param path: The path of the file you want to get.
    :returns: The found file, or a 404 error.
    """
    path, is_dir = files.split_path(path_str or '/')

    proxy = None
    if proxy_id is not None:
        proxy = models.Proxy.query.filter_by(id=proxy_id).one_or_none()
        if flask.session.get('proxy_id') != str(proxy.id):
            # TODO: Show nice cookie error message
            assert 0

    if proxy is None or proxy.deleted:
        proxy = helpers.get_or_404(
            models.Proxy,
            flask.session['proxy_id'],
            also_error=lambda p: p.deleted
        )

    if proxy.expired:
        raise APIException(
            'This proxy has expired, please reload the page',
            f'The proxy "{proxy.id}" has expired.',
            APICodes.OBJECT_EXPIRED,
            400,
        )

    found_file = None
    if is_dir:
        for f in ['index.html']:
            found_file = proxy.get_file([*path, f])
            if found_file:
                break
    else:
        found_file = proxy.get_file(path)

    if found_file is None or found_file.is_directory:
        raise APIException(
            'The given file could not be found.',
            f'The path "{path_str}" was not found in this proxy.',
            APICodes.OBJECT_NOT_FOUND, 404
        )
    ctype, _ = mimetypes.guess_type(path_str)
    res = flask.Response(found_file.open(), mimetype=ctype)
    # res.headers['Content-Security-Policy'] = proxy.csp_header
    res.headers['Referrer-Policy'] = 'unsafe-url'
    return res
