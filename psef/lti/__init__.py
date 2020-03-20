import enum
import typing as t

from .. import PsefFlask

__all__: t.List[str] = []


class LTIVersion(enum.Enum):
    v1_1 = enum.auto()
    v1_3 = enum.auto()

    def __to_json__(self) -> str:
        return self.name


def init_app(app: PsefFlask) -> None:
    from . import v1_1, v1_3
    v1_1.init_app(app)
    v1_3.init_app(app)
