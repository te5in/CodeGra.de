import typing as t

from cryptography.hazmat.primitives.asymmetric.rsa import (
    RSAPublicKey, RSAPrivateKey
)

T_SELF = t.TypeVar('T_SELF', bound='Registration')

_POSSIBLE_KEYS = t.Union[str, bytes, RSAPrivateKey, RSAPublicKey]


class Registration:
    def get_issuer(self) -> str:
        ...

    def set_issuer(self: T_SELF, issuer: str) -> T_SELF:
        ...

    def get_client_id(self) -> str:
        ...

    def set_client_id(self: T_SELF, client_id: str) -> T_SELF:
        ...

    def get_key_set(self) -> t.Optional[str]:
        ...

    def set_key_set(self: T_SELF, key_set: t.Optional[str]) -> T_SELF:
        ...

    def get_key_set_url(self) -> t.Optional[str]:
        ...

    def set_key_set_url(self: T_SELF, key_set_url: t.Optional[str]) -> T_SELF:
        ...

    def get_auth_token_url(self) -> str:
        ...

    def set_auth_token_url(self: T_SELF, auth_token_url: str) -> T_SELF:
        ...

    def get_auth_login_url(self) -> str:
        ...

    def set_auth_login_url(self: T_SELF, auth_login_url: str) -> T_SELF:
        ...

    def get_tool_private_key(self) -> _POSSIBLE_KEYS:
        ...

    def set_tool_private_key(
        self: T_SELF, tool_private_key: _POSSIBLE_KEYS
    ) -> T_SELF:
        ...
