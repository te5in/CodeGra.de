from .. import Tester


def get_provs(db):
    return db.engine.execute('SELECT * from "LTIProvider" ORDER BY id'
                             ).fetchall()


def compare_provs(with_id, without_id):
    assert len(with_id) == len(without_id)
    for p1, p2 in zip(with_id, without_id):
        p1_dict = dict(p1)
        assert 'updates_lti1p1_id' in p1_dict
        p1_dict.pop('updates_lti1p1_id')

        p2_dict = dict(p2)
        assert 'updates_lti1p1_id' not in p2_dict

        assert p1_dict == p2_dict


class UpgradeTester(Tester):
    provs = None

    def load_data(self):
        self.provs = get_provs(self.db)

    def check(self):
        assert self.provs
        new_provs = get_provs(self.db)
        compare_provs(new_provs, self.provs)
        for prov in new_provs:
            assert prov.updates_lti1p1_id is None


class DowngradeTester(Tester):
    provs = None

    def load_data(self):
        self.provs = get_provs(self.db)
        assert self.provs[-1].updates_lti1p1_id == self.provs[0].id

    def check(self):
        assert self.provs
        new_provs = get_provs(self.db)
        compare_provs(self.provs, new_provs)
