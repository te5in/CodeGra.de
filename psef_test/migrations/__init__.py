import abc


class Tester(abc.ABC):
    def __init__(self, db, **_):
        self.db = db
        self.users = None

    @staticmethod
    def do_test():
        return True

    @abc.abstractmethod
    def load_data(self):
        raise NotImplementedError

    @abc.abstractmethod
    def check(self):
        raise NotImplementedError
