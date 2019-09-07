import json


class Session:
    class Response:
        def json(self):
            raise json.decoder.JSONDecodeError('err', '', -1)

        def raise_for_status(self):
            pass

    def delete(self, _, **__):
        return Session.Response()

    get = post = patch = put = delete

    def __enter__(self):
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object):
        pass
