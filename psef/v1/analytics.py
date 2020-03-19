from cg_json import JSONResponse

from . import api
from .. import auth, models, helpers, registry


@api.route("/analytics/<int:ana_id>", methods=['GET'])
def get_analytics(ana_id: int) -> JSONResponse[models.AnalticsWorkspace]:
    workspace = helpers.get_or_404(models.AnalticsWorkspace, ana_id)
    auth.ensure_can_see_analytics_workspace(workspace)
    return JSONResponse.make(workspace)


@api.route('/analytics/<int:ana_id>/<data_source>')
def get_data_source(ana_id: int,
                    data_source: str) -> JSONResponse[models.BaseDataSource]:
    workspace = helpers.get_or_404(models.AnalticsWorkspace, ana_id)
    auth.ensure_can_see_analytics_workspace(workspace)
    data_source = registry[data_source]
    return JSONResponse.make(data_source(workspace))
