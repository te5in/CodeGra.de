import uuid

import pytest

import helpers
import psef.models as m
import psef.signals as signals
from psef.permissions import GlobalPermission as GPerm


@pytest.mark.parametrize(
    'lms,iss', [
        ('Brightspace', 'https://partners.brightspace.com'),
        ('Canvas', 'https://canvas.instructure.com'),
    ]
)
def test_get_providers(
    test_client, describe, logged_in, admin_user, teacher_user, watch_signal,
    lms, iss
):
    with describe('pre-check'), logged_in(admin_user):
        test_client.req(
            'get',
            '/api/v1/lti1.3/providers/',
            200,
            result=[],
        )

    with describe('setup'), logged_in(admin_user):
        provider = helpers.create_lti1p3_provider(
            test_client,
            lms,
            iss=iss,
            client_id=str(uuid.uuid4()) + '_lms=' + lms,
        )
        assig_created = watch_signal(signals.ASSIGNMENT_CREATED)

    with describe('should get registered providers'), logged_in(admin_user):
        test_client.req(
            'get',
            '/api/v1/lti1.3/providers/',
            200,
            result=[provider],
        )

    with describe(
        'should be possible to add multiple providers for the same LMS'
    ), logged_in(admin_user):
        provider2 = helpers.create_lti1p3_provider(
            test_client,
            lms,
            iss=iss,
            client_id=str(uuid.uuid4()) + '_lms=' + lms,
        )

    with describe('should get registered providers'), logged_in(admin_user):
        test_client.req(
            'get',
            '/api/v1/lti1.3/providers/',
            200,
            result=[provider, provider2],
        )

    with describe('should not be visible to non-admin users'
                  ), logged_in(teacher_user):
        test_client.req(
            'get',
            '/api/v1/lti1.3/providers/',
            200,
            result=[],
        )

    assert assig_created.was_send_n_times(0)


@pytest.mark.parametrize(
    'lms,iss', [('Canvas', 'https://canvas.instructure.com')]
)
def test_create_lti_provider(
    test_client, describe, lms, iss, session, logged_in
):
    with describe('setup'):
        admin_user = helpers.create_user_with_perms(
            session, [], [], [GPerm.can_manage_lti_providers]
        )
        normal_user = helpers.create_user_with_perms(session, [], [], [])
        data = {'lms': lms, 'iss': iss, 'intended_use': 'AA'}

    with describe('admin can create a provider'), logged_in(admin_user):
        prov = test_client.req(
            'post', '/api/v1/lti1.3/providers/', 200, data=data
        )
        test_client.req('get', '/api/v1/lti1.3/providers/', 200, result=[prov])

    with describe('cannot create provider without iss'), logged_in(admin_user):
        test_client.req(
            'post', '/api/v1/lti1.3/providers/', 400, data={**data, 'iss': ''}
        )
        test_client.req('get', '/api/v1/lti1.3/providers/', 200, result=[prov])

    with describe('normal user cannot create a provider'):
        with logged_in(normal_user):
            test_client.req(
                'post', '/api/v1/lti1.3/providers/', 403, data=data
            )

        with logged_in(admin_user):
            # Should not be a new one created
            test_client.req(
                'get', '/api/v1/lti1.3/providers/', 200, result=[prov]
            )


@pytest.mark.parametrize(
    'lms,iss', [('Canvas', 'https://canvas.instructure.com')]
)
def test_update_lti_provider(
    test_client, describe, lms, iss, session, logged_in
):
    with describe('setup'):
        admin_user = helpers.create_user_with_perms(
            session, [], [], [GPerm.can_manage_lti_providers]
        )
        normal_user = helpers.create_user_with_perms(session, [], [], [])
        with logged_in(admin_user):
            prov = test_client.req(
                'post',
                '/api/v1/lti1.3/providers/',
                200,
                data={'lms': lms, 'iss': iss, 'intended_use': 'AA'},
            )
            url = f'/api/v1/lti1.3/providers/{helpers.get_id(prov)}'

    with describe('admin can update a provider'), logged_in(admin_user):
        prov = test_client.req('patch', url, 200, data={'client_id': 'aa'})
        test_client.req('get', '/api/v1/lti1.3/providers/', 200, result=[prov])

    with describe('normal user cannot update a provider'
                  ), logged_in(normal_user):
        test_client.req(
            'patch', url + '?secret=aa', 403, data={'auth_token_url': 'err'}
        )
        with logged_in(admin_user):
            test_client.req(
                'get', '/api/v1/lti1.3/providers/', 200, result=[prov]
            )

    with describe('normal user can update provider with secret'
                  ), logged_in(normal_user):
        test_client.req(
            'patch',
            f'{url}?secret={prov["edit_secret"]}',
            200,
            data={'auth_token_url': 'DEP 1'},
            result={
                **prov,
                'auth_token_url': 'DEP 1',
                'edit_secret': None,
            },
        )
        with logged_in(admin_user):
            prov, = test_client.req(
                'get',
                '/api/v1/lti1.3/providers/',
                200,
                result=[{**prov, 'auth_token_url': 'DEP 1'}]
            )

    with describe('cannot finalize before all info is filled in'
                  ), logged_in(admin_user):
        test_client.req('patch', url, 400, data={'finalize': True})

    with describe('cannot edit after it is finalized'), logged_in(admin_user):
        prov = test_client.req(
            'patch',
            url,
            200,
            data={
                'client_id': 'id',
                'auth_token_url': 'c',
                'auth_login_url': 'd',
                'key_set_url': 'asdf',
                'finalize': True,
            },
            result={'__allow_extra__': True, 'finalized': True}
        )
        test_client.req('patch', url, 403, data={'client_id': 'e'})
        test_client.req('get', url, 200, result=prov)


@pytest.mark.parametrize('lms', ['Canvas'])
def test_get_json_config_for_provider(
        test_client, describe, lms, logged_in, admin_user, app, monkeypatch
):
    with describe('setup'), logged_in(admin_user):
        prov = helpers.create_lti1p3_provider(test_client, lms)
        url = f'/api/v1/lti1.3/providers/{helpers.get_id(prov)}/config'
        ext_url = f'{uuid.uuid4()}.com'
        monkeypatch.setitem(app.config, 'EXTERNAL_URL', ext_url)

    with describe(
        'should be possible to get json config without being logged in'
    ):
        test_client.req('get', url, 200, result={
            '__allow_extra__': True,
            'target_link_uri': f'{ext_url}/api/v1/lti1.3/launch',
            'oidc_initiation_url': f'{ext_url}/api/v1/lti1.3/login',
        })


@pytest.mark.parametrize('lms,err_code', [('Moodle', 200), ('Canvas', 400)])
def test_setting_deadline_for_assignment(
    test_client, describe, logged_in, admin_user, session, tomorrow, lms,
    err_code
):
    with describe('setup'), logged_in(admin_user):
        prov = helpers.to_db_object(
            helpers.create_lti1p3_provider(test_client, lms), m.LTI1p3Provider
        )
        course, _ = helpers.create_lti1p3_course(test_client, session, prov)

        assig = helpers.create_lti1p3_assignment(session, course)

    with describe('should maybe be possible to update the deadline'
                  ), logged_in(admin_user):
        test_client.req(
            'patch',
            f'/api/v1/assignments/{helpers.get_id(assig)}',
            err_code,
            data={'deadline': tomorrow.isoformat()}
        )


@pytest.mark.parametrize('lms', ['Canvas'])
def test_get_jwks_for_provider(
    test_client, describe, lms, logged_in, admin_user
):
    with describe('setup'), logged_in(admin_user):
        prov = helpers.to_db_object(
            helpers.create_lti1p3_provider(test_client, lms), m.LTI1p3Provider
        )
        url = f'/api/v1/lti1.3/providers/{helpers.get_id(prov)}/jwks'

    with describe(
        'should be possible to get json config without being logged in'
    ):
        test_client.req(
            'get', url, 200, result={'keys': [prov.get_public_jwk()]}
        )
