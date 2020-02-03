import typing as t

from .registration import Registration
from .deep_link_resource import DeepLinkResource


class DeepLink:
    def __init__(
        self,
        registration: Registration,
        deployment_id: str,
        deep_link_settings: t.Mapping[str, object],
    ):
        ...

    def get_message_jwt(self, resources: t.List[DeepLinkResource]
                        ) -> t.Dict[str, object]:
        ...

    def encode_jwt(self, message: t.Dict[str, object]) -> bytes:
        ...

    def get_response_jwt(self, resources: t.List[DeepLinkResource]) -> bytes:
        ...

    def get_response_form_html(self, jwt_val: bytes) -> str:
        ...

    def output_response_form(self, resources: t.List[DeepLinkResource]) -> str:
        ...
