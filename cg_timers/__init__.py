import time
import typing as t
import contextlib
from functools import wraps

import structlog

logger = structlog.get_logger()

T_CAL = t.TypeVar('T_CAL', bound=t.Callable)

__all__ = ['timed_code', 'timed_function']


@contextlib.contextmanager
def timed_code(code_block_name: str, **other_keys: object
               ) -> t.Generator[t.Callable[[], float], None, None]:
    start_time = time.time()
    logger.info(
        'Starting timed code block',
        timed_code_block=code_block_name,
        **other_keys
    )
    end_time: t.Optional[float] = None

    try:
        yield lambda: (end_time or time.time()) - start_time
    except:
        exc_info = True
        raise
    else:
        exc_info = False
    finally:
        end_time = time.time()
        logger.info(
            'Finished timed code block',
            timed_code_block=code_block_name,
            exc_info=exc_info,
            exception_occurred=exc_info,
            elapsed_time=end_time - start_time,
            **other_keys,
        )


def timed_function(fun: T_CAL) -> T_CAL:
    @wraps(fun)
    def _wrapper(*args: object, **kwargs: object) -> object:
        with timed_code(fun.__qualname__):
            return fun(*args, **kwargs)

    return t.cast(T_CAL, _wrapper)
