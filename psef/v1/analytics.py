from cg_json import JSONResponse

from . import api
from .. import auth, models, helpers, registry


@api.route("/analytics/<int:ana_id>", methods=['GET'])
def get_analytics(ana_id: int) -> JSONResponse[models.AnalyticsWorkspace]:
    workspace = helpers.get_or_404(models.AnalyticsWorkspace, ana_id)
    auth.ensure_can_see_analytics_workspace(workspace)
    return JSONResponse.make(workspace)


@api.route(
    '/analytics/<int:ana_id>/data_sources/<data_source_name>', methods=['GET']
)
def get_data_source(
    ana_id: int,
    data_source_name: str,
) -> JSONResponse[models.BaseDataSource]:
    workspace = helpers.get_or_404(models.AnalyticsWorkspace, ana_id)
    auth.ensure_can_see_analytics_workspace(workspace)
    data_source = registry.analytics_data_sources[data_source_name]

    return JSONResponse.make(data_source(workspace))
