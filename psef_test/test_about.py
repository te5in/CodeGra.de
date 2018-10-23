# SPDX-License-Identifier: AGPL-3.0-only

from psef import tasks, models


def test_about_health_status(test_client, app, monkeypatch):
    monkeypatch.setitem(app.config, 'HEALTH_KEY', None)
    test_client.req(
        'get',
        '/api/v1/about',
        200,
        query={'health': None},
        result={
            'version': object,
            'features': dict,
        },
    )

    monkeypatch.setitem(app.config, 'HEALTH_KEY', 'good key')
    test_client.req(
        'get',
        '/api/v1/about',
        200,
        query={'health': 'not key'},
        result={
            'version': object,
            'features': dict,
        },
    )

    raise_error = False

    class Inspect:
        def __call__(self):
            if raise_error:
                raise Exception('ERR!')
            return True

        def ping(self):
            return self()

        def first(self):
            return self()

    monkeypatch.setattr(tasks.celery.control, 'inspect', Inspect)

    test_client.req(
        'get',
        '/api/v1/about',
        200,
        query={'health': 'good key'},
        result={
            'version': object,
            'features': dict,
            'health': {
                'application': True,
                'database': True,
                'celery': True,
                'uploads': True,
                'mirror_uploads': True,
            },
        }
    )

    raise_error = True

    test_client.req(
        'get',
        '/api/v1/about',
        500,
        query={'health': 'good key'},
        result={
            'version': object,
            'features': dict,
            'health': {
                'application': True,
                'database': True,
                'celery': False,
                'uploads': True,
                'mirror_uploads': True,
            },
        },
    )

    monkeypatch.setattr(models.User, 'query', Inspect())

    test_client.req(
        'get',
        '/api/v1/about',
        500,
        query={'health': 'good key'},
        result={
            'version': object,
            'features': dict,
            'health': {
                'application': True,
                'database': False,
                'celery': False,
                'uploads': True,
                'mirror_uploads': True,
            },
        },
    )
