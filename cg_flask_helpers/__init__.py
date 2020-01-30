"""Various helpers for flask used in CodeGrade.

SPDX-License-Identifier: AGPL-3.0-only
"""
import typing as t

import flask
import celery

from cg_celery import TaskStatus

T = t.TypeVar('T')  # pylint: disable=invalid-name


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

    else:

        @flask.after_this_request
        def after(res: flask.Response) -> flask.Response:
            """The entire callback that is executed at the end of the request.
            """
            if res.status_code < 400:
                fun()
            return res

        return after


class EmptyResponse(flask.Response):  # pylint: disable=too-many-ancestors
    """An empty response.

    This is a subtype of :py:class:`werkzeug.wrappers.Response` where the body
    is empty and the status code is always 204.
    """

    def __init__(self, content: str, *args: t.Any, **kwargs: t.Any) -> None:
        # EmptyResponse should always be empty
        assert not content
        # EmptyResponse always has a status of 204
        assert kwargs.get('status') == 204

        super().__init__(content, *args, **kwargs)

    @classmethod
    def make(cls) -> 'EmptyResponse':
        """Create an empty response.
        """
        return cls('', status=204)


make_empty_response = EmptyResponse.make  # pylint: disable=invalid-name
