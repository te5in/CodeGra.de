from cg_json import JSONResponse

from . import api
from .. import auth, models, helpers, registry, exceptions


@api.route("/analytics/<int:ana_id>", methods=['GET'])
def get_analytics(ana_id: int) -> JSONResponse[models.AnalyticsWorkspace]:
    workspace = helpers.get_or_404(models.AnalyticsWorkspace, ana_id)
    auth.AnalyticsWorkspacePermissions(workspace).ensure_may_see()
    return JSONResponse.make(workspace)


@api.route(
    '/analytics/<int:ana_id>/data_sources/<data_source_name>', methods=['GET']
)
def get_data_source(
    ana_id: int,
    data_source_name: str,
) -> JSONResponse[models.BaseDataSource]:
    workspace = helpers.get_or_404(models.AnalyticsWorkspace, ana_id)
    auth.AnalyticsWorkspacePermissions(workspace).ensure_may_see()
    data_source = registry.analytics_data_sources[data_source_name]
    if not data_source.should_include(workspace=workspace):
        raise exceptions.APIException(
            'The given data source is not enabled for this workspace', (
                f'The data source {data_source_name} is not enabled for'
                f' worspace {ana_id}.'
            ), exceptions.APICodes.OBJECT_NOT_FOUND, 404
        )

    return JSONResponse.make(data_source(workspace))
