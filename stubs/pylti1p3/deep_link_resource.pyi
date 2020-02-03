import typing as t

T_SELF = t.TypeVar('T_SELF', bound='DeepLinkResource')


class DeepLinkResource:
    def to_dict(self) -> t.Dict[str, object]:
        ...

    def set_custom_params(self: T_SELF, value: t.Dict[str, str]) -> T_SELF:
        ...

    def set_title(self: T_SELF, value: str) -> T_SELF:
        ...
