import uuid

from cg_json import JSONResponse

from . import api
from ..auth import TaskResultPermissions
from ..models import TaskResult
from ..helpers import get_or_404


@api.route('/task_results/<uuid:task_result_id>')
def get_task_result(task_result_id: uuid.UUID) -> JSONResponse[TaskResult]:
    """Get the state of a task result.

    .. :quickref: Task result; Get a single task result.


    .. note:

        To check if the task failed you should use the ``state`` attribute of
        the returned object as the status code of the response will still be
        200. It is 200 as we successfully fulfilled the request, which was
        getting the task result.

    :param task_result_id: The task result to get.
    :returns: The retrieved task result.
    """
    result = get_or_404(TaskResult, task_result_id)
    TaskResultPermissions(result).ensure_may_see()
    return JSONResponse.make(result)
