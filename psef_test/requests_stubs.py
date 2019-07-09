class Session:
    class Response:
        def raise_for_status(self):
            pass

    def delete(self, _):
        return Session.Response()

    def get(self, _):
        return Session.Response()

    def post(self, _, **__):
        return Session.Response()

    def patch(self, _, **__):
        return Session.Response()

    def __enter__(self):
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object):
        pass
