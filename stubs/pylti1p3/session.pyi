from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

_JWT_BODY = Dict[str, object]
_STATE_PARAMS = Dict[str, object]


class SessionService(ABC):
    _session_prefix: str

    @abstractmethod
    def get_launch_data(self, key: str) -> Optional[_JWT_BODY]:
        raise NotImplementedError

    @abstractmethod
    def save_launch_data(self, key: str, jwt_body: _JWT_BODY) -> None:
        raise NotImplementedError

    @abstractmethod
    def save_nonce(self, nonce: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def check_nonce(self, nonce: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def save_state_params(self, state: str, params: _STATE_PARAMS) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_state_params(self, state: str) -> _STATE_PARAMS:
        raise NotImplementedError
