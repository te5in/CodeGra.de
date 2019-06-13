import secrets

_PASS_LEN = 64


def make_password(nbytes: int = _PASS_LEN) -> str:
    assert nbytes > 32, 'Not secure enough'
    return secrets.token_hex(_PASS_LEN)
