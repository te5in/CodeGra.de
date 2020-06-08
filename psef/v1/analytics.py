"""
This module defines all API routes for the analytics workspaces.

.. warning:

    All these routes should be considered non stable. Expect them to change
    their behavior within a few releases.

SPDX-License-Identifier: AGPL-3.0-only
"""
from cg_json import JSONResponse

from . import api
from .. import auth, models, helpers, registry, exceptions


@api.route("/analytics/<int:ana_id>", methods=['GET'])
def get_analytics(ana_id: int) -> JSONResponse[models.AnalyticsWorkspace]:
    """Get a :class:`.models.AnalyticsWorkspace`.

    .. :quickref: Analytics; Get a analytics workspace.

    .. warning::

        This route should be considered beta, its behavior and/or existence
        will change.

    :param int ana_id: The id of the workspace to get.
    """
    workspace = helpers.get_or_404(
        models.AnalyticsWorkspace,
        ana_id,
        also_error=lambda a: not a.assignment.is_visible
    )
    auth.AnalyticsWorkspacePermissions(workspace).ensure_may_see()
    return JSONResponse.make(workspace)


@api.route(
    '/analytics/<int:ana_id>/data_sources/<data_source_name>', methods=['GET']
)
def get_data_source(
    ana_id: int,
    data_source_name: str,
) -> JSONResponse[models.BaseDataSource]:
    """Get a data source within a :class:`.models.AnalyticsWorkspace`.

    .. :quickref: Analytics; Get a data source of a workspace.

    .. warning::

        This route should be considered beta, its behavior and/or existence
        will change.

    :param int ana_id: The id of the workspace in which the datasource should
        be retrieved.
    :param string data_source_name: The name of the data source to retrieve.
    """
    workspace = helpers.get_or_404(
        models.AnalyticsWorkspace,
        ana_id,
        also_error=lambda a: not a.assignment.is_visible
    )
    auth.AnalyticsWorkspacePermissions(workspace).ensure_may_see()

    data_source = registry.analytics_data_sources[data_source_name](workspace)
    if not data_source.should_include():
        raise exceptions.APIException(
            'The given data source is not enabled for this workspace', (
                f'The data source {data_source_name} is not enabled for'
                f' worspace {ana_id}.'
            ), exceptions.APICodes.OBJECT_NOT_FOUND, 404
        )

    return JSONResponse.make(data_source)
