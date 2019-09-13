import json
import random


class Session:
    class Response:
        @property
        def status_code(self) -> None:
            return 200

        def json(self):
            raise json.decoder.JSONDecodeError('err', '', -1)

        def raise_for_status(self):
            pass

    def delete(self, _, **__):
        return Session.Response()

    def __init__(self, *args):
        pass

    get = post = patch = put = delete

    def __enter__(self):
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object):
        pass
