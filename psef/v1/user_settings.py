from cg_json import JSONResponse

from . import api
from .. import models


@api.route('/settings/<setting_name>', methods=['PATCH'])
def update_setting(setting_name: str) -> JSONResponse[models.SettingBase]:
    pass
