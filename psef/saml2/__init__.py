import xml
import uuid
import typing as t
import xml.etree.ElementTree as ET
from datetime import timedelta

import furl
import flask
import flask_jwt_extended as flask_jwt
from flask import request, session
from typing_extensions import Final
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from defusedxml.ElementTree import fromstring as defused_xml_fromstring
from onelogin.saml2.settings import OneLogin_Saml2_Settings
from onelogin.saml2.constants import OneLogin_Saml2_Constants
from onelogin.saml2.idp_metadata_parser import OneLogin_Saml2_IdPMetadataParser

import cg_json

from .. import PsefFlask, models, helpers, current_app
from ..models import db
from ..helpers import readable_join

MDUI_NAMESPACE: Final = 'urn:oasis:names:tc:SAML:metadata:ui'
_URLS = ['https://samltest.id/saml/idp']

_SAML_SESSION_PREFIX = 'SAML_'

saml = flask.Blueprint(
    name='saml',
    import_name=__name__,
)  # pylint: disable=invalid-name

_MAX_BLOB_AGE = timedelta(minutes=5)


def _session_key(key: str) -> str:
    return f'{_SAML_SESSION_PREFIX}_{key}'


def _make_saml_url() -> furl.furl:
    return furl.furl(current_app.config['EXTERNAL_URL']).add(
        path=['api', 'sso', 'saml2'],
    )


def _make_error(title: str, message: str) -> t.Tuple[str, int]:
    return (
        flask.render_template(
            'error_page.j2', error_title=title, error_message=message
        ), 400
    )


class AttributeNames:
    EMAIL: Final = 'urn:oid:0.9.2342.19200300.100.1.3'
    FULL_NAME: Final = 'urn:oid:2.5.4.3'
    DISPLAY_NAME: Final = 'urn:oid:2.16.840.1.113730.3.1.241'
    UID: Final = 'urn:oid:0.9.2342.19200300.100.1.1'


def init_saml_auth(req, provider: models.Saml2Provider):
    idp = OneLogin_Saml2_IdPMetadataParser.parse_remote(_URLS[0])['idp']

    bindings = 'urn:oasis:names:tc:SAML:2.0:bindings'
    entityId = _make_saml_url().add(path=['metadata', provider.id]).tostr()
    acs_url = _make_saml_url().add(path=['acs', provider.id]).tostr()
    # yapf: disable
    settings = OneLogin_Saml2_Settings(
        settings={
            "strict": not current_app.config['DEBUG'],
            "debug": current_app.config['DEBUG'],
            'security': {
                'authnRequestsSigned': True,
                'WantAssertionsSigned': True,
            },
            "sp": {
                "entityId": entityId,
                "assertionConsumerService": {
                    "url": acs_url,
                    "binding": f"{bindings}:HTTP-POST"
                },
                "NameIDFormat": OneLogin_Saml2_Constants.NAMEID_PERSISTENT,
                "x509cert": provider.public_x509_cert,
                "privateKey": provider.private_key,
            },
            "idp": provider.provider_metadata,
            "contactPerson": {
                "support": {
                    "givenName": "Support",
                    "emailAddress": "support@codegrade.com",
                },
            },
            "organization": {
                "en-US": {
                    "name": "CodeGrade",
                    "displayname": "CodeGrade",
                    "url": current_app.config['EXTERNAL_URL'],
                },
            },
        }
    )
    # yapf: enable
    auth = OneLogin_Saml2_Auth(req, old_settings=settings)
    return auth


def prepare_flask_request():
    # If server is behind proxys or balancers use the HTTP_X_FORWARDED fields
    url_data = furl.furl(request.url)

    https = (
        'on' if not current_app.config['DEBUG'] or request.scheme == 'https'
        else 'off'
    )
    return {
        'https': https,
        'http_host': request.host,
        'server_port': url_data.port,
        'script_name': request.path,
        'get_data': request.args.copy(),
        # Uncomment if using ADFS as IdP, https://github.com/onelogin/python-saml/pull/144
        # 'lowercase_urlencoding': True,
        'post_data': request.form.copy()
    }


@saml.route('/login/<uuid:provider_id>', methods=['GET'])
def do_saml_login(provider_id: uuid.UUID):
    provider = helpers.get_or_404(models.Saml2Provider, provider_id)
    req = prepare_flask_request()
    auth = init_saml_auth(req, provider)

    blob_id = str(uuid.uuid4())
    session[_session_key('BLOB_ID')] = blob_id
    return_to = furl.furl(current_app.config['EXTERNAL_URL']).add(
        path=['sso_login', blob_id],
        args=request.args,
    ).tostr()

    sso_built_url = auth.login(return_to)
    session[_session_key('AuthNRequestID')] = auth.get_last_request_id()
    return flask.redirect(sso_built_url)


@saml.route('/acs/<uuid:provider_id>', methods=['POST'])
def get_acs(provider_id: uuid.UUID):
    req = prepare_flask_request()
    provider = helpers.get_or_404(models.Saml2Provider, provider_id)
    auth = init_saml_auth(req, provider)

    try:
        request_id = session[_session_key('AuthNRequestID')]
        del session[_session_key('AuthNRequestID')]
    except KeyError:
        request_id = str(uuid.uuid4())

    auth.process_response(request_id=request_id)
    errors = auth.get_errors()

    if errors or not auth.is_authenticated():
        if auth.is_authenticated():
            error_title = 'Something went wrong during login.'
        else:
            error_title = 'Logging in was unsuccessful.'

        error_message = error_title
        if auth.get_settings().is_debug_active():
            error_message = auth.get_last_error_reason() or error_title

        return _make_error(
            error_title,
            flask.escape(error_message),
        )

    if auth.get_nameid_format() != OneLogin_Saml2_Constants.NAMEID_PERSISTENT:
        return _make_error(
            'Incorrect nameId type',
            (
                'Got a wrong type of name id, so we cannot log you in. (Got:'
                ' {})'
            ).format(
                auth.get_nameid_format(),
            ),
        )

    attributes = auth.get_attributes()
    name_id = auth.get_nameid()
    username = attributes.get(AttributeNames.UID)
    email = attributes.get(AttributeNames.EMAIL)
    full_name = attributes.get(
        AttributeNames.FULL_NAME, attributes.get(AttributeNames.DISPLAY_NAME)
    )

    if not (username and email and full_name):
        missing_data = [
            name for name, value in [
                ('username', username),
                ('email', email),
                ('name', full_name),
            ] if not value
        ]
        return _make_error(
            'Not all required data found',
            'The following data is missing: {}'.format(
                readable_join(missing_data)
            ),
        )

    blob_id = uuid.UUID(session[_session_key('BLOB_ID')])
    user = models.UserSamlProvider.get_or_create_user(
        name_id=name_id,
        saml2_provider=provider,
        username=username[0],
        email=email[0],
        full_name=full_name[0],
    )

    blob = models.BlobStorage(
        json={
            'provider_id': str(provider_id),
            'user_id': user.id,
        },
        blob_id=blob_id,
    )
    db.session.add(blob)
    db.session.commit()

    return flask.redirect(auth.redirect_to(request.form['RelayState']))


@saml.route('/jwts/<uuid:blob_id>', methods=['POST'])
def get_jwt_from_success_full_login(
    blob_id: uuid.UUID
) -> cg_json.JSONResponse[t.Dict[str, str]]:
    if _session_key('BLOB_ID') in session:
        session_blob_id = uuid.UUID(session[_session_key('BLOB_ID')])
    else:
        session_blob_id = None

    blob = helpers.filter_single_or_404(
        models.BlobStorage,
        models.BlobStorage.id == blob_id,
        models.BlobStorage.id == session_blob_id,
        with_for_update=True,
        also_error=lambda blob: blob.age > _MAX_BLOB_AGE,
    )
    del session[_session_key('BLOB_ID')]

    user = helpers.get_or_404(models.User, blob.as_json()['user_id'])
    db.session.delete(blob)
    db.session.commit()

    return cg_json.JSONResponse.make(
        {
            'access_token':
                flask_jwt.create_access_token(
                    identity=user.id,
                    fresh=True,
                    expires_delta=timedelta(days=1),
                )
        }
    )


@saml.route('/metadata/<uuid:provider_id>', methods=['GET'])
def get_metadata(provider_id: uuid.UUID):
    req = prepare_flask_request()
    auth = init_saml_auth(
        req, helpers.get_or_404(models.Saml2Provider, provider_id)
    )
    settings = auth.get_settings()
    metadata = settings.get_sp_metadata()

    tree: ET.Element = defused_xml_fromstring(metadata)
    NSMAP = {
        **OneLogin_Saml2_Constants.NSMAP,
        'mdui': MDUI_NAMESPACE,
    }

    def make_tag(ns: str, tagname: str) -> str:
        return '{{{}}}{}'.format(NSMAP.get(ns), tagname)

    desc = tree.find('.//md:SPSSODescriptor', NSMAP)
    assert desc is not None
    ext = desc.find('./md:Extensions'.format(), NSMAP)
    if ext is None:
        ext = desc.makeelement(make_tag('md', 'Extensions'), {})
        desc.insert(0, ext)

    uiinfo = ext.makeelement(make_tag('mdui', 'UIInfo'), {})

    for lang in ['nl', 'en']:
        display_name = uiinfo.makeelement(
            make_tag('mdui', 'DisplayName'), {'xml:lang': lang}
        )
        display_name.text = 'CodeGrade'
        uiinfo.append(display_name)

        description = uiinfo.makeelement(
            make_tag('mdui', 'Description'), {'xml:lang': lang}
        )
        description.text = 'Deliver engaging feedback on code.'
        uiinfo.append(description)

        info_url = uiinfo.makeelement(
            make_tag('mdui', 'InformationURL'), {'xml:lang': lang}
        )
        info_url.text = current_app.config['EXTERNAL_URL']
        uiinfo.append(info_url)

    logo = uiinfo.makeelement(
        make_tag('mdui', 'Logo'), {
            'height': '249',
            'width': '1263'
        }
    )
    logo.text = furl.furl(current_app.config['EXTERNAL_URL']
                          ).add(path='static/img/codegrade-inv.png').tostr()
    uiinfo.append(logo)

    ext.append(uiinfo)

    metadata = ET.tostring(tree)
    errors = settings.validate_metadata(metadata)

    if errors:
        return _make_error(
            'Error generating metadata',
            flask.escape(readable_join(list(errors))),
        )
    else:
        resp = flask.make_response(metadata, 200)
        resp.headers['Content-Type'] = 'text/xml'
        return resp


def init_app(app: PsefFlask) -> None:
    app.register_blueprint(saml, url_prefix='/api/sso/saml2/')
