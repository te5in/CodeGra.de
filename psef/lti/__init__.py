import typing as t

from . import v1_1, v1_3
from .. import PsefFlask

__all__: t.List[str] = []


def init_app(app: PsefFlask) -> None:
    v1_1.init_app(app)
    v1_3.init_app(app)
