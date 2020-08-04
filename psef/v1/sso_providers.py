"""This module defines all API routes with the main directory "sso_providers".

The APIs are used to create/get SSO Providers.

SPDX-License-Identifier: AGPL-3.0-only
"""
import typing as t

from cg_json import JSONResponse

from . import api
from .. import auth, models, helpers
from ..models import db
from ..permissions import GlobalPermission as GPerm


@api.route('/sso_providers/', methods=['GET'])
def get_all_sso_providers() -> JSONResponse[t.Sequence[models.Saml2Provider]]:
    """Get all SSO Providers.

    .. :quickref: SSO Provider; Get all SSO Providers for this instance.
    """
    return JSONResponse.make(
        models.Saml2Provider.query.order_by(
            models.Saml2Provider.created_at.asc()
        ).all()
    )


@api.route('/sso_providers/', methods=['POST'])
@auth.permission_required(GPerm.can_manage_sso_providers)
def create_sso_providers() -> JSONResponse[models.Saml2Provider]:
    """Register a new SSO Provider in this instance.

    .. :quickref: SSO Provider; Create a new SSO Providers in this instance.

    Users will be able to login using the registered provider.

    :>json metadata_url: The url where we can download the metadata for the IdP
        connected to this provider.
    :>json name: If no name can be found in the metadata this name will be
        displayed to users when choosing login methods.

    :returns: The just created provider.
    """
    with helpers.get_from_request_transaction() as [get, _]:
        metadata_url = get('metadata_url', str)
        name = get('name', str)

    prov = models.Saml2Provider(metadata_url=metadata_url, name=name)
    db.session.add(prov)
    prov.check_metadata_url()
    db.session.commit()

    return JSONResponse.make(prov)
