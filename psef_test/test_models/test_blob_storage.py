import json

import psef.models as m


def test_blob_storage_json(describe, session, make_function_spy):
    with describe('can create using json'):
        obj = {'a': [5]}
        blob = m.BlobStorage(json=obj)
        session.add(blob)
        session.commit()

    with describe('can retrieve json with `as_json` and it should be cached'):
        spy = make_function_spy(json, 'loads')
        blob = m.BlobStorage.query.get(blob.id)

        got_obj = blob.as_json()
        assert got_obj == obj
        assert got_obj is not obj
        assert blob.as_json() == obj
        assert blob.as_json() is blob.as_json()
        assert spy.called_amount == 1
