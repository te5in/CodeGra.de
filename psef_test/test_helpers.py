import requests

import psef.helpers as h


def test_broker_session(monkeypatch):
    with h.BrokerSession('', '', 'http://echo.jsontest.com') as ses:
        assert ses.get('/code/5').json() == {'code': '5'}
