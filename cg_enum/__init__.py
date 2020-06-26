import enum
import typing as t


class CGEnum(enum.Enum):
    def __getattr__(self, name: str) -> t.Any:
        if name.startswith('is_'):
            try:
                found = type(self)[name[len('is_'):]]
                return self is found
            except KeyError:
                pass

        raise AttributeError
