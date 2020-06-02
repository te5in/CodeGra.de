import uuid

import helpers


def make_provider(
    test_client,
    lms,
    iss=None,
    client_id=None,
    auth_token_url=None,
    auth_login_url=None,
    key_set_url=None,
    auth_audience=None
):
    prov = test_client.req(
        'post',
        '/api/v1/lti1.3/providers/',
        200,
        data={
            'lms': lms,
            'iss': iss or str(uuid.uuid4()),
            'intended_use': 'A test provider',
        }
    )

    def make_data(**data):
        return {k: v or 'http://' + str(uuid.uuid4()) for k, v in data.items()}

    return test_client.req(
        'patch',
        f'/api/v1/lti1.3/providers/{helpers.get_id(prov)}',
        200,
        data=make_data(
            client_id=client_id,
            auth_token_url=auth_token_url,
            auth_login_url=auth_login_url,
            auth_audience=auth_audience,
            key_set_url=key_set_url,
            finalize=True,
        )
    )
