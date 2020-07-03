from .. import Tester


def get_auto_tests(db):
    return db.engine.execute('SELECT * from "AutoTest" ORDER BY id').fetchall()


class UpgradeTester(Tester):
    def load_data(self):
        auto_tests = get_auto_tests(self.db)
        assert auto_tests
        assert all('prefer_teacher_revision' not in at for at in auto_tests)

    def check(self):
        auto_tests = get_auto_tests(self.db)
        assert auto_tests
        assert all(not at['prefer_teacher_revision'] for at in auto_tests)


class DowngradeTester(Tester):
    def load_data(self):
        auto_tests = get_auto_tests(self.db)
        assert auto_tests
        assert all('prefer_teacher_revision' in at for at in auto_tests)

    def check(self):
        auto_tests = get_auto_tests(self.db)
        assert auto_tests
        assert all('prefer_teacher_revision' not in at for at in auto_tests)
