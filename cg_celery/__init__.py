"""This module defines a subclass of Celery to be used in CodeGrade projects

SPDX-License-Identifier: AGPL-3.0-only
"""

import typing as t
import logging as system_logging

import structlog
from flask import Flask, g, has_app_context
from celery import Celery as _Celery
from celery import signals

logger = structlog.get_logger()

if t.TYPE_CHECKING:  # pragma: no cover
    # pylint: disable-all
    T = t.TypeVar('T', bound=t.Callable)

    class CeleryTask(t.Generic[T]):
        @property
        def __call__(self) -> T:
            ...

        @property
        def delay(self) -> T:
            # This hax is for sphinx as it can't parse the source otherwise
            return lambda *args, **kwargs: None  # type: ignore

        @property
        def apply_async(self) -> t.Any:
            ...

    class Celery:
        def __init__(self, _name: str) -> None:
            self.conf: t.MutableMapping[t.Any, t.Any] = {}
            self.control: t.Any

        @t.overload
        def task(self, _callback: T) -> CeleryTask[T]:
            ...

        @t.overload
        def task(
            self,
            *,
            autoretry_for: t.Iterable[t.Type[Exception]],
            retry_kwargs: t.Dict[str, object],
            retry_backoff: bool,
            retry_jitter: bool = True,
            retry_backoff_max: t.Optional[int] = None,
        ) -> t.Callable[[T], CeleryTask[T]]:
            ...

        @t.overload
        def task(self, **kwargs: t.Union[int, bool]
                 ) -> t.Callable[[T], CeleryTask[T]]:
            ...

        def task(self, *args: object, **kwargs: object) -> t.Any:
            # `CeleryTask()` is returned here as this code is also executed
            # when generating the documentation.
            if len(args) == 1:
                return CeleryTask()
            else:
                return self.task
else:
    Celery = _Celery


class CGCelery(Celery):
    """A subclass of celery that makes sure tasks are always called with a
    flask app context
    """

    def __init__(self, name: str, signals: t.Any) -> None:
        super().__init__(name)
        self._signals = signals
        self._flask_app: t.Any = None
        self.__enable_logging()

        if t.TYPE_CHECKING:  # pragma: no cover

            class TaskBase:
                """Example task base for Mypy annotations
                """
                request: t.Any
                name: str
        else:
            # self.Task is available in the `Celery` object.
            TaskBase = self.Task  # pylint: disable=access-member-before-definition,invalid-name

        outer_self = self

        class _ContextTask(TaskBase):
            def __call__(self, *args: t.Any, **kwargs: t.Any) -> t.Any:
                # This is not written by us but taken from here:
                # https://web.archive.org/web/20150617151604/http://slides.skien.cc/flask-hacks-and-best-practices/#15

                # pylint: disable=protected-access
                assert outer_self._flask_app

                if has_app_context():
                    return TaskBase.__call__(self, *args, **kwargs)

                log = logger.new(
                    request_id=self.request.id,
                    in_celery=True,
                    task_name=self.name,
                    # pylint: disable=protected-access
                    base_url=outer_self._flask_app.config.get('EXTERNAL_URL'),
                )

                log.info(
                    'Starting task',
                    argsrepr=repr(args),
                    kwargsrepr=repr(kwargs),
                )

                if outer_self._flask_app.testing:
                    g.request_id = self.request.id
                    g.queries_amount = 0
                    g.queries_total_duration = 0
                    g.queries_max_duration = None
                    g.query_start = None
                    result = TaskBase.__call__(self, *args, **kwargs)
                    logger.bind(
                        queries_amount=g.queries_amount,
                        queries_max_duration=g.queries_max_duration,
                        queries_total_duration=g.queries_total_duration,
                    )
                    return result
                with outer_self._flask_app.app_context():  # pragma: no cover
                    g.request_id = self.request.id
                    g.queries_amount = 0
                    g.queries_total_duration = 0
                    g.queries_max_duration = None
                    g.query_start = None
                    result = TaskBase.__call__(self, *args, **kwargs)
                    logger.bind(
                        queries_amount=g.queries_amount,
                        queries_max_duration=g.queries_max_duration,
                        queries_total_duration=g.queries_total_duration,
                    )
                    return result

        self.Task = _ContextTask  # pylint: disable=invalid-name

    def init_flask_app(self, app: Flask) -> None:
        self.conf.update(app.config['CELERY_CONFIG'])
        # This is a weird class that is like a dict but not really.
        self.conf.update({
            'task_ignore_result': True,
            'celery_hijack_root_logger': False,
            'worker_log_format': '%(message)s',
        })
        self._flask_app = app

    def __enable_logging(self) -> None:
        system_logging.getLogger('cg_celery').setLevel(system_logging.DEBUG)

        @self._signals.before_task_publish.connect(weak=False)
        def __celery_before_task_publish(
            sender: str, headers: object, **_: object
        ) -> None:  # pragma: no cover
            logger.info('Publishing task', sender=sender, headers=headers)

        @self._signals.after_task_publish.connect(weak=False)
        def __celery_after_task_publish(
            sender: str, headers: object, **_: object
        ) -> None:  # pragma: no cover
            logger.info('Published task', sender=sender, headers=headers)

        @self._signals.task_success.connect(weak=False)
        def __celery_success(**kwargs: object) -> None:
            logger.info(
                'Task finished',
                result=kwargs['result'],
            )

        @self._signals.task_failure.connect(weak=False)
        def __celery_failure(**_: object) -> None:  # pragma: no cover
            logger.error(
                'Task failed',
                exc_info=True,
            )

        @self._signals.task_revoked.connect(weak=False)
        def __celery_revoked(**kwargs: object) -> None:  # pragma: no cover
            logger.info(
                'Task revoked',
                terminated=kwargs['terminated'],
                signum=kwargs['signum'],
                expired=kwargs['expired'],
            )

        @self._signals.task_unknown.connect(weak=False)
        def __celery_unkown(**kwargs: object) -> None:  # pragma: no cover
            logger.warning(
                'Unknown task received',
                task_name=kwargs['name'],
                request_id=kwargs['id'],
                raw_message=kwargs['message'],
            )

        @self._signals.task_rejected.connect(weak=False)
        def __celery_rejected(**kwargs: object) -> None:  # pragma: no cover
            logger.warning(
                'Rejected task received',
                raw_message=kwargs['message'],
            )
