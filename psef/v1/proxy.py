"""This file contains all routes for proxies.

SPDX-License-Identifier: AGPL-3.0-only
"""
import uuid
import mimetypes

import flask
import werkzeug
import structlog

from . import api
from .. import app, files, models, helpers, features
from ..exceptions import APICodes, APIException

logger = structlog.get_logger()


def _show_session_error() -> werkzeug.wrappers.Response:
    return flask.render_template(
        'error_page.j2',
        error_title='Could not load session',
        error_message=(
            """
        There was a problem settings cookies, it seems like we are not allowed
        to do so. Cookies are required for this feature, as we need them to
        remember which submission you are viewing. They will not be used for
        analytical purposes.

        <br>
        In some browsers, Safari for example, you need to allow third party
        cookies.
        """
        ),
    )


def _get_base_url() -> str:
    base_url = app.config['EXTERNAL_PROXY_URL']
    if not base_url:
        assert app.debug, 'EXTERNAL_PROXY_URL should be set in production'
        base_url = app.config['EXTERNAL_URL'] + '/api/v1/proxy'
    return base_url


@api.route('/proxy/<uuid:proxy_id>/<path:path_str>', methods=['POST'])
@features.feature_required(features.Feature.RENDER_HTML)
def start_proxy(
    proxy_id: uuid.UUID, path_str: str
) -> werkzeug.wrappers.Response:
    proxy = helpers.filter_single_or_404(
        models.Proxy,
        models.Proxy.id == proxy_id,
        with_for_update=True,
        also_error=lambda p: p.deleted or p.times_used > 0 or p.expired,
    )
    proxy.times_used += 1
    flask.session['proxy_id'] = str(proxy.id)
    models.db.session.commit()
    return flask.redirect(
        _get_base_url() + '/' + str(proxy.id) + '/' + path_str, code=303
    )


@api.route('/proxy/<uuid:proxy_id>/<path:path_str>', methods=['GET'])
@features.feature_required(features.Feature.RENDER_HTML)
def second_step_starting_proxy(
    proxy_id: uuid.UUID, path_str: str
) -> werkzeug.wrappers.Response:
    proxy = helpers.get_or_404(
        models.Proxy,
        proxy_id,
        also_error=lambda p: p.deleted or p.times_used > 1 or p.expired,
    )
    if flask.session.get('proxy_id') != str(proxy.id):
        return _show_session_error()

    return flask.redirect(_get_base_url() + '/' + path_str, code=303)


@api.route('/proxy/', methods=['GET'])
@api.route('/proxy/<path:path_str>', methods=['GET'])
@features.feature_required(features.Feature.RENDER_HTML)
def get_proxy_file(path_str: str = '') -> werkzeug.wrappers.Response:
    """Get a file for the given proxy.

    :param proxy_id: The proxy in which you want to get a file.
    :param path: The path of the file you want to get.
    :returns: The found file, or a 404 error.
    """
    path, is_dir = files.split_path(path_str or '/')

    proxy = None

    if 'proxy_id' not in flask.session:
        return _show_session_error()

    proxy = helpers.get_or_404(
        models.Proxy,
        flask.session['proxy_id'],
        also_error=lambda p: p.deleted
    )

    if proxy.expired:
        raise APIException(
            'This proxy has expired, please reload the page.',
            f'The proxy "{proxy.id}" has expired.',
            APICodes.OBJECT_EXPIRED,
            400,
        )

    found_file = None
    if is_dir:
        for f in ['index.html', 'index.HTML', 'index.htm', 'index.HTM']:
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
    res.headers['Content-Security-Policy'] = proxy.csp_header
    return res
