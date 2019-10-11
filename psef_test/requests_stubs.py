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

    def make_req_stub(self, meth):
        def req(*args, **kwargs):
            self.calls.append({
                'args': args,
                'kwargs': kwargs,
                'method': meth,
            })
            return Session.Response()

        return req

    def __init__(self, *args):
        self.calls = []
        self.get = self.make_req_stub('get')
        self.post = self.make_req_stub('post')
        self.patch = self.make_req_stub('patch')
        self.put = self.make_req_stub('put')
        self.delete = self.make_req_stub('delete')

    def reset(self):
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object):
        pass
