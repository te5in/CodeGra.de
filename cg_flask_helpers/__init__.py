import typing as t

import flask
import celery

from cg_celery import TaskStatus

T = t.TypeVar('T')


def callback_after_this_request(
    fun: t.Callable[[], object],
) -> t.Callable[[T], T]:
    """Execute a callback after this request without changing the response.

    :param fun: The callback to execute after the current request.
    :returns: The function that will execute after this request that does that
        the response as argument, so this function wraps your given callback.
    """
    if celery.current_task:
        @celery.current_app.after_this_task
        def after_task(res: TaskStatus) -> None:
            if res == TaskStatus.success:
                fun()

        return after_task

    @flask.after_this_request
    def after(res: flask.Response) -> flask.Response:
        """The entire callback that is executed at the end of the request.
        """
        if res.status_code < 400:
            fun()
        return res

    return after
