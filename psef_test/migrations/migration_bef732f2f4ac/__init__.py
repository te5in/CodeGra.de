import subprocess
from itertools import groupby

import pytest

from .. import Tester


class UpgradeTester(Tester):
    def get_users(self):
        return self.db.engine.execute('SELECT * FROM "User" ORDER BY id'
                                      ).fetchall()

    @staticmethod
    def do_test():
        return True

    def load_data(self):
        self.users = self.get_users()

    def check(self):
        cur_users = self.get_users()
        assert len(cur_users) > 0
        assert len(self.users) == len(cur_users), 'No users should be deleted'

        for cur_user, old_user in zip(cur_users, self.users):
            assert cur_user.id == old_user.id
            assert cur_user.username == old_user.username
            assert hasattr(old_user, 'lti_user_id')
            assert not hasattr(cur_user, 'lti_user_id')

        user_lti_provider_connections = {
            k: list(v)
            for k, v in groupby(
                self.db.engine.execute(
                    'SELECT * FROM "user_lti-provider" ORDER BY user_id'
                ).fetchall(),
                lambda el: el.user_id,
            )
        }

        # User 5 was not an LTI user
        assert set(user_lti_provider_connections.keys()) == {1, 2, 3, 4, 6}

        def check_connections(user_id, wanted_ids, lti_user_id):
            found = [
                c.lti_provider_id
                for c in user_lti_provider_connections[user_id]
            ]
            found_set = set(found)
            assert len(found) == len(found_set)
            assert found_set == set(wanted_ids)
            assert all(
                c.lti_user_id == lti_user_id
                for c in user_lti_provider_connections[user_id]
            )

        check_connections(1, ['lti_prov_1', 'lti_prov_2'], '11')
        check_connections(2, ['lti_prov_1'], '22')
        check_connections(3, ['lti_prov_1', 'lti_prov_2'], '33')
        check_connections(4, ['lti_prov_1'], '44')
        check_connections(6, ['lti_prov_2'], '66')


class DowngradeTester(Tester):
    @staticmethod
    def do_test():
        return False

    def load_data(self):
        pass

    def check(self):
        pass
