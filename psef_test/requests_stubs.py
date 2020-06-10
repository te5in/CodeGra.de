import json
import random


def session_maker():
    class _Response:
        @property
        def status_code(self) -> None:
            return 200

        @property
        def headers(self):
            return []

        @property
        def content(self):
            return '{}'

        def json(self):
            raise json.decoder.JSONDecodeError('err', '', -1)

        def raise_for_status(self):
            pass

    class _Session:
        Response = _Response
        all_calls = []

        def make_req_stub(self, meth):
            def req(*args, **kwargs):
                data = {
                    'args': args,
                    'kwargs': kwargs,
                    'method': meth,
                }
                self.calls.append(data)
                _Session.all_calls.append(data)
                return self.Response()

            return req

        def __init__(self, *args):
            self.calls = []
            self.get = self.make_req_stub('get')
            self.post = self.make_req_stub('post')
            self.patch = self.make_req_stub('patch')
            self.put = self.make_req_stub('put')
            self.delete = self.make_req_stub('delete')

        @classmethod
        def reset_cls(cls):
            cls.Response = _Response
            cls.all_calls = []

        def reset(self):
            self.calls = []

        def __enter__(self):
            return self

        def __exit__(
            self, exc_type: object, exc_value: object, traceback: object
        ):
            pass

    return _Session


Session = session_maker()
