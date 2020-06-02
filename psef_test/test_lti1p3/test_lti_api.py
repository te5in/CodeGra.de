import uuid

import pytest

import psef.signals as signals
from lti1p3_helpers import make_provider


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
        provider = make_provider(
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
        provider2 = make_provider(
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
