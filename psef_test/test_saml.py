import io
import subprocess

import helpers


def test_create_provider(
    test_client, stub_function, logged_in, describe, admin_user, session
):
    with describe('setup'), logged_in(admin_user):
        user = helpers.create_user_with_role(session, 'BLAH', [])

    with describe('Can create provider'), logged_in(admin_user):
        provider1 = helpers.create_sso_provider(
            test_client,
            stub_function,
            'SSO Prov 1',
            ui_info={
                'name': 'A name',
                'description': 'A desc',
                'logo': None,
            }
        )
        assert provider1['ui_info']['name'] == 'A name'
        assert provider1['ui_info']['description'] == 'A desc'
        assert provider1['ui_info']['logo'] is None

    with describe('Can create a provider where no metadata is returned'
                  ), logged_in(admin_user):
        provider2 = helpers.create_sso_provider(
            test_client,
            stub_function,
            'SSO Prov 2',
            description='TEST SSO',
            ui_info={
                'name': None,
                'description': None,
                'logo': None,
            }
        )
        assert provider2['ui_info']['name'] == 'SSO Prov 2'
        assert provider2['ui_info']['description'] == 'TEST SSO'
        assert provider2['ui_info']['logo'] is None

    with describe('Cannot create a provider as a normal user'
                  ), logged_in(user):
        helpers.create_sso_provider(test_client, stub_function, 'ERR', err=403)

    with describe('Can list created providers without logging in'):
        test_client.req(
            'get',
            '/api/v1/sso_providers/',
            200,
            result=[provider1, provider2],
        )

    with describe('Can retrieve default logo of providers'):
        response = test_client.get(
            f'/api/v1/sso_providers/{helpers.get_id(provider1)}/default_logo'
        )
        assert response.status_code == 200
        popen = subprocess.Popen(['file', '-'],
                                 stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        file_stdout, _ = popen.communicate(input=response.get_data())
        assert b'SVG' in file_stdout
        assert b'image' in file_stdout
