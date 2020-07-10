# SPDX-License-Identifier: AGPL-3.0-only
import pytest

import psef.models as m
import psef.features as f


def test_about_features(test_client, app, monkeypatch):
    test_client.req(
        'get',
        '/api/v1/about',
        200,
        result={
            'version': app.config['VERSION'],
            'commit': str,
            'features': {
                k.name: bool(v)
                for k, v in app.config['FEATURES'].items()
            },
        }
    )


def test_disable_features(
    test_client, logged_in, ta_user, monkeypatch, app, error_template
):
    monkeypatch.setitem(
        app.config['FEATURES'], f.Feature.BLACKBOARD_ZIP_UPLOAD, False
    )
    with logged_in(ta_user):
        res = test_client.req(
            'post',
            '/api/v1/assignments/5/submissions/',
            400,
            result={
                **error_template,
                'disabled_feature': {'name': str},
            }
        )
        assert 'feature is not enabled' in res['message']
