import typing as t

from cg_json import JSONResponse

from . import api
from .. import auth, models, helpers
from ..models import db
from ..permissions import GlobalPermission as GPerm


@api.route('/sso_providers/', methods=['GET'])
def get_all_sso_providers() -> JSONResponse[t.Sequence[models.Saml2Provider]]:
    return JSONResponse.make(
        models.Saml2Provider.query.order_by(
            models.Saml2Provider.created_at.asc()
        ).all()
    )


@api.route('/sso_providers/', methods=['POST'])
@auth.permission_required(GPerm.can_manage_sso_providers)
def create_sso_providers() -> JSONResponse[models.Saml2Provider]:
    with helpers.get_from_request_transaction() as [get, _]:
        metadata_url = get('metadata_url', str)
        name = get('name', str)

    prov = models.Saml2Provider(metadata_url=metadata_url, name=name)
    db.session.add(prov)
    prov.check_metadata_url()
    db.session.commit()

    return JSONResponse.make(prov)
