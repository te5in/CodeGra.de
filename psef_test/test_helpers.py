import requests

import psef.helpers as h


def test_broker_session(monkeypatch):
    with h.BrokerSession('', '', 'http://www.mocky.io') as ses:
        assert ses.get('/v2/5d9e5e71320000c532329d38').json() == {'code': 5}
