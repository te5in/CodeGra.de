import copy
import uuid
import pprint
from re import compile as regex
from datetime import timedelta

import jwt
import furl
import flask
import pytest
import freezegun
import pylti1p3.names_roles
import pylti1p3.assignments_grades
from defusedxml.ElementTree import fromstring as defused_xml_fromstring

import helpers
import psef.models as m
import psef.signals as signals
import psef.lti.v1_3 as lti1p3
from cg_dt_utils import DatetimeWithTimezone

LTI_JWT_SECRET = str(uuid.uuid4())

DEEP_LINK = '__CG_EXPECT_DEEP_LINK__'


@pytest.fixture
def monkeypatched_passback(monkeypatch, stub_function_class):
    stub = stub_function_class()
    monkeypatch.setattr(
        pylti1p3.assignments_grades.AssignmentsGradesService, 'put_grade', stub
    )
    yield stub


@pytest.fixture(autouse=True)
def monkeypatched_get_members(monkeypatch, stub_function_class):
    stub = stub_function_class(lambda: [])
    monkeypatch.setattr(
        pylti1p3.names_roles.NamesRolesProvisioningService, 'get_members', stub
    )
    yield stub


@pytest.fixture(autouse=True)
def monkeypatched_validate_jwt(monkeypatch, stub_function_class):
    stub = stub_function_class(
        lambda self: self, pass_self=True, with_args=True
    )
    monkeypatch.setattr(lti1p3.MessageLaunch, 'validate_jwt_signature', stub)
    yield stub


def remove_from(d1, key):
    res = copy.copy(d1)
    del res[key]
    return res


def merge(d1, d2):
    res = copy.copy(d1)

    for k, v2 in d2.items():
        v1 = d1.get(k)
        if isinstance(v1, dict) and isinstance(v2, dict):
            res[k] = merge(v1, v2)
        else:
            res[k] = v2

    return res


def replace_values(base_data, replace_dict):
    if isinstance(base_data, list):
        return [replace_values(item, replace_dict) for item in base_data]
    elif isinstance(base_data, dict):
        res = {}
        for key, value in base_data.items():
            if isinstance(value, list):
                res[key] = replace_values(value, replace_dict)
            elif isinstance(value, dict):
                res[key] = replace_values(value, replace_dict)
            elif value in replace_dict:
                res[key] = replace_dict[value]
            else:
                res[key] = value
        return res
    elif base_data in replace_dict:
        return replace_dict[base_data]
    return copy.copy(base_data)


BASE_LAUNCH_DATA = {
    'aud': 'client_id',
    'exp': 1590999956,
    'nbf': 1590998156,
    'iat': 1590998156,
    'sub': '91f41e6b-a507-4168-9347-204b9316f03d_6324',
    'given_name': 'CodeGrade',
    'family_name': 'Administrator',
    'name': 'CodeGrade Administrator',
    'email': 'User@email.com',
    'https://purl.imsglobal.org/spec/lti/claim/message_type':
        'LtiResourceLinkRequest',
    'https://purl.imsglobal.org/spec/lti/claim/version': '1.3.0',
    'https://purl.imsglobal.org/spec/lti/claim/deployment_id': 'Deployment.id',
    'https://purl.imsglobal.org/spec/lti/claim/target_link_uri': 'Launch.url',
    'https://purl.imsglobal.org/spec/lti/claim/resource_link': {
        'id': 'Assignment.id',
        'title': 'Assignment.name',
        'description': None,
    },
    'https://purl.imsglobal.org/spec/lti/claim/roles': [
        'http://purl.imsglobal.org/vocab/lis/v2/membership#Administrator',
        'http://purl.imsglobal.org/vocab/lis/v2/institution/person#Student',
        'http://purl.imsglobal.org/vocab/lis/v2/institution/person#Learner',
        'http://purl.imsglobal.org/vocab/lis/v2/institution/person#Instructor',
        'http://purl.imsglobal.org/vocab/lis/v2/institution/person#Mentor',
        'http://purl.imsglobal.org/vocab/lis/v2/institution/person#Staff',
        'http://purl.imsglobal.org/vocab/lis/v2/institution/person#Administrator',
    ],
    'https://purl.imsglobal.org/spec/lti/claim/context': {
        'id': 'Course.id',
        'label': 'Course.label',
        'title': 'Course.title',
        'type': [
            'http://purl.imsglobal.org/vocab/lis/v2/course#CourseOffering',
        ],
    },
    'https://purl.imsglobal.org/spec/lti/claim/lis': {
        'course_offering_sourcedid': 'example_lms:CodeGrade1',
        'course_section_sourcedid': 'example_lms:CodeGrade1',
    },
    'https://purl.imsglobal.org/spec/lti/claim/launch_presentation': {
        'locale': 'en-us',
    },
    'https://purl.imsglobal.org/spec/lti-ags/claim/endpoint': {
        'scope': [
            'https://purl.imsglobal.org/spec/lti-ags/scope/lineitem',
            'https://purl.imsglobal.org/spec/lti-ags/scope/lineitem.readonly',
            'https://purl.imsglobal.org/spec/lti-ags/scope/result.readonly',
            'https://purl.imsglobal.org/spec/lti-ags/scope/score',
        ],
        'lineitems': 'lineitems.endpoint',
    },
    'https://purl.imsglobal.org/spec/lti/claim/custom': {
        'cg_username_0': 'cg_username',
        'cg_deadline_0': 'cg_deadline',
        'cg_available_at_0': 'cg_available_at',
        'cg_resource_id_0': 'cg_resource_id',
        'cg_lock_date_0': 'cg_lock_date',
    },
    'https://purl.imsglobal.org/spec/lti-nrps/claim/namesroleservice': {
        'context_memberships_url': 'context_memberships_url',
        'service_versions': ['2.0'],
    },
}

CANVAS_DATA = merge(
    BASE_LAUNCH_DATA, {
        'iss': 'https://canvas.instructure.com',
        'https://purl.imsglobal.org/spec/lti/claim/custom': {
            'cg_deadline_1': 'cg_deadline',
            'cg_is_published_0': 'cg_is_published',
            'cg_resource_id_1': 'cg_resource_id',
            'cg_lock_date_1': 'cg_lock_date',
        }
    }
)

BRIGHTSPACE_DATA = merge(
    BASE_LAUNCH_DATA,
    {
        'iss': 'https://partners.brightspace.com',
        'http://www.brightspace.com': {
            'tenant_id': '41b632b6-ff74-4288-b3f1-7ffb6eb14bb4',
            'org_defined_id': 'CodeGrade.A1',
            'user_id': 'User.id',
            'username': 'User.username',
            'ResourceLink.id.history': '',
            'Context.id.history': '',
        },
    },
)


def make_launch_data(base, provider, override_replace={}):
    provider = m.LTI1p3Provider.query.get(helpers.get_id(provider))

    return replace_values(
        base,
        {
            'cg_username': 'Test username',
            'cg_deadline': '',
            'cg_available_at': '',
            'cg_resource_id': '',
            'cg_lock_date': '',
            'Assignment.name': 'Test Assignment 1',
            'Course.label': 'Test Course 1',
            'Course.id': str(uuid.uuid4()),
            'User.id': str(uuid.uuid4()),
            'User.username': 'Test username',
            'Assignment.id': str(uuid.uuid4()),
            'iss': provider.iss,
            'client_id': provider.client_id,
            **override_replace,
        },
    )


def do_oidc_login(test_client, provider, with_id=False):
    provider = m.LTI1p3Provider.query.get(helpers.get_id(provider))

    redirect_uri = str(uuid.uuid4())
    login_hint = str(uuid.uuid4())
    url = '/api/v1/lti1.3/login'
    if with_id:
        url += '/' + str(provider.id)

    redirect = test_client.post(
        url,
        data={
            'target_link_uri': redirect_uri,
            'iss': provider.iss,
            'client_id': provider.client_id,
            'login_hint': login_hint,
        }
    )
    assert redirect.status_code == 303
    assert redirect.headers['Location'].startswith(provider._auth_login_url)
    return furl.furl(redirect.headers['Location']).asdict()


def do_lti_launch(
    test_client, provider, data, oidc_result, status, with_id=False
):
    oidc_params = dict(oidc_result['query']['params'])
    url = '/api/v1/lti1.3/launch'
    if with_id:
        url += '/' + str(provider.id)
    response = test_client.post(
        url,
        data={
            'id_token':
                jwt.encode(
                    {**data, 'nonce': oidc_params['nonce']},
                    LTI_JWT_SECRET,
                    algorithm='HS256',
                ),
            'state': oidc_params['state'],
        },
    )
    if status == DEEP_LINK:
        return response
    assert response.status_code == 303
    url = furl.furl(response.headers['Location'])
    blob_id = dict(url.asdict()['query']['params'])['blob_id']
    return test_client.req(
        'post',
        '/api/v1/lti/launch/2?extended',
        status,
        data={
            'blob_id': blob_id,
        }
    )


def do_oidc_and_lti_launch(
    test_client, provider, data, status=200, with_id=False
):
    oidc = do_oidc_login(test_client, provider, with_id=with_id)
    launch = do_lti_launch(test_client, provider, data, oidc, status, with_id)
    return oidc, launch


@pytest.mark.parametrize(
    'launch_data,lms,iss', [
        (BRIGHTSPACE_DATA, 'Brightspace', 'https://partners.brightspace.com'),
        (CANVAS_DATA, 'Canvas', 'https://canvas.instructure.com'),
    ]
)
def test_do_simple_launch(
    test_client, describe, logged_in, admin_user, watch_signal, launch_data,
    lms, iss, monkeypatched_validate_jwt, monkeypatched_passback
):
    with describe('setup'), logged_in(admin_user):
        provider = helpers.create_lti1p3_provider(
            test_client,
            lms,
            iss=iss,
            client_id=str(uuid.uuid4()) + '_lms=' + lms
        )
        user_added = watch_signal(signals.USER_ADDED_TO_COURSE)
        assig_created = watch_signal(signals.ASSIGNMENT_CREATED)
        lti_assig_id = str(uuid.uuid4())
        lti_assig_id2 = str(uuid.uuid4())
        lti_course_id = str(uuid.uuid4())

    with describe('Initial launch creates assignment and course'):
        _, launch_result = do_oidc_and_lti_launch(
            test_client,
            provider,
            make_launch_data(
                launch_data,
                provider,
                {
                    'Assignment.id': lti_assig_id,
                    'Course.id': lti_course_id,
                },
            ),
        )
        assert monkeypatched_validate_jwt.called_amount == 1

        assert user_added.was_send_once
        assert monkeypatched_passback.called_amount == 1
        passback_arg = monkeypatched_passback.all_args[0]
        assert len(passback_arg) == 1
        assert passback_arg[0].get_score_given() is None
        assert passback_arg[0].get_activity_progress() == 'Initialized'

        assert assig_created.was_send_once
        assert assig_created.signal_arg.lti_assignment_id == lti_assig_id

        assert launch_result['version'] == 'v1_3'
        assert launch_result['data']['type'] == 'normal_result'
        course = launch_result['data']['course']
        assig = launch_result['data']['assignment']
        assert assig['id'] == assig_created.signal_arg.id
        assert course['is_lti']

    with describe('Second launch does not create assignment again'):
        _, launch_result2 = do_oidc_and_lti_launch(
            test_client,
            provider,
            make_launch_data(
                launch_data,
                provider,
                {
                    'Course.id': lti_course_id,
                    'Assignment.id': lti_assig_id,
                },
            ),
        )
        assert monkeypatched_validate_jwt.called_amount == 1

        assert user_added.was_not_send

        assert assig_created.was_not_send
        assert launch_result2['data']['course']['id'] == course['id']
        assert launch_result2['data']['assignment']['id'] == assig['id']

    with describe('New launch in same course only creates assignment'):
        _, launch_result3 = do_oidc_and_lti_launch(
            test_client,
            provider,
            make_launch_data(
                launch_data,
                provider,
                {
                    'Course.id': lti_course_id,
                    'Assignment.id': lti_assig_id2,
                },
            ),
        )
        assert monkeypatched_validate_jwt.called_amount == 1

        assert user_added.was_not_send

        assert assig_created.was_send_once
        assert launch_result3['data']['course']['id'] == course['id']
        assert launch_result3['data']['assignment']['id'] != assig['id']


@pytest.mark.parametrize('with_id', [True, False])
def test_do_oidc_with_get(test_client, lti1p3_provider, with_id, describe):
    with describe('setup'):
        redirect_uri = str(uuid.uuid4())
        login_hint = str(uuid.uuid4())
        url = '/api/v1/lti1.3/login'
        if with_id:
            url += '/' + str(lti1p3_provider.id)

    with describe('can do oidc launch with GET request'), test_client as c:
        redirect = c.get(
            furl.furl(url).add({
                'target_link_uri': redirect_uri,
                'iss': lti1p3_provider.iss,
                'login_hint': login_hint,
            }).tostr(),
        )
        assert redirect.status_code == 303
        assert redirect.headers['Location'].startswith(
            lti1p3_provider._auth_login_url
        )
        assert flask.session


def test_with_wrong_nonce(
    test_client, describe, logged_in, admin_user, monkeypatched_passback
):
    with describe('setup'), logged_in(admin_user):
        lti_assig_id = str(uuid.uuid4())
        lti_course_id = str(uuid.uuid4())
        lms = 'Canvas'
        provider = helpers.create_lti1p3_provider(
            test_client,
            lms,
            iss='https://canvas.instructure.com',
            client_id=str(uuid.uuid4()) + '_lms=' + lms
        )

    with describe('can do oidc launch with GET request'), test_client as c:
        oidc = do_oidc_login(c, provider)
        with c.session_transaction() as sess:
            s_service = lti1p3.flask.FlaskSessionService(
                lti1p3.flask.FlaskRequest(force_post=False)
            )
            sess[s_service._get_key('lti-nonce')] = 'Not correct'

        response = do_lti_launch(
            c,
            provider,
            make_launch_data(
                CANVAS_DATA,
                provider,
                {
                    'Assignment.id': lti_assig_id,
                    'Course.id': lti_course_id,
                },
            ),
            oidc,
            400,
        )
        assert response['message'] == 'Invalid Nonce'


def test_direct_deep_link_launch(test_client, describe, logged_in, admin_user):
    with describe('setup'), logged_in(admin_user):
        canvas_provider = helpers.create_lti1p3_provider(
            test_client,
            'Canvas',
            iss='https://canvas.instructure.com',
            client_id=str(uuid.uuid4()) + '_lms=' + 'Canvas'
        )
        return_url = f'https://{uuid.uuid4()}.com'
        deep_link_data = {
            lti1p3.claims.MESSAGE_TYPE: 'LtiDeepLinkingRequest',
            lti1p3.claims.DEEP_LINK: {
                'data': 'DP_DATA',
                'deep_link_return_url': return_url,
                'accept_types': ['ltiResourceLink'],
                'accept_presentation_document_targets': 'PRES',
            },
        }
        canvas_launch_data = make_launch_data(
            merge(CANVAS_DATA, deep_link_data), canvas_provider, {}
        )

    with describe('deep link to canvas should directly return resource'):
        _, launch = do_oidc_and_lti_launch(
            test_client, canvas_provider, canvas_launch_data, status=DEEP_LINK
        )
        form = launch.data
        parsed = defused_xml_fromstring(form.decode('utf8'))
        assert parsed.tag == 'html'
        form, = parsed.findall('body/form')
        assert form.attrib['action'] == return_url
        assert form.attrib['method'] == 'POST'
        child, = form.getchildren()
        assert child.attrib['name'] == 'JWT'
        assert child.attrib['type'] == 'hidden'
        jwt_value = child.attrib['value']
        assert jwt.decode(jwt_value, verify=False)


def test_real_deep_link_launch(test_client, describe, logged_in, admin_user):
    with describe('setup'), logged_in(admin_user):
        brightspace_provider = helpers.create_lti1p3_provider(
            test_client,
            'Brightspace',
            iss='https://partners.brightspace.com',
            client_id=str(uuid.uuid4()) + '_lms=' + 'Lichtruimte'
        )
        return_url = f'https://{uuid.uuid4()}.com'
        deep_link_data = {
            lti1p3.claims.MESSAGE_TYPE: 'LtiDeepLinkingRequest',
            lti1p3.claims.DEEP_LINK: {
                'data': 'DP_DATA',
                'deep_link_return_url': return_url,
                'accept_types': ['ltiResourceLink'],
                'accept_presentation_document_targets': 'PRES',
            },
        }
        launch_data = make_launch_data(
            merge(BRIGHTSPACE_DATA, deep_link_data), brightspace_provider, {}
        )

        def get_new_deep_link():
            _, launch = do_oidc_and_lti_launch(
                test_client, brightspace_provider, launch_data
            )
            assert launch['data']['type'] == 'deep_link'
            blob_id = launch['data']['deep_link_blob_id']
            auth_token = launch['data']['auth_token']
            return auth_token, f'/api/v1/lti1.3/deep_link/{blob_id}'

    with describe('have to provide correct auth token to use blob id'):
        auth_token, url = get_new_deep_link()
        res = test_client.req(
            'post',
            url,
            403,
            data={
                'auth_token': f'WRONG_{auth_token}',
                'name': 'assig_name',
                'deadline': 'NOT A DEADLINE',
            },
            result={
                '__allow_extra__': True,
                'message': regex('not provide the correct token'),
            }
        )

    with describe('too old blob id is also rejected'):
        auth_token, url = get_new_deep_link()
        with freezegun.freeze_time(
            DatetimeWithTimezone.utcnow() + timedelta(days=2)
        ):
            test_client.req(
                'post',
                url,
                400,
                result={
                    '__allow_extra__': True,
                    'message': regex('^This deep linking session has expired'),
                }
            )

    with describe('returns deep link form if all is correct'):
        auth_token, url = get_new_deep_link()
        deadline = DatetimeWithTimezone.utcnow() + timedelta(days=4)
        res = test_client.req(
            'post',
            url,
            200,
            data={
                'auth_token': auth_token,
                'name': 'assig_name',
                'deadline': deadline.isoformat(),
            },
            result={
                'jwt': str,
                'url': return_url,
            }
        )
        jwt_parsed = jwt.decode(res['jwt'], verify=False)
        content_items = jwt_parsed[
            'https://purl.imsglobal.org/spec/lti-dl/claim/content_items']
        assert isinstance(content_items, list)
        assert len(content_items) == 1
        assert content_items[0]['title'] == 'assig_name'
        assert content_items[0]['submission']['endDateTime'
                                              ] == deadline.isoformat()


def test_launch_with_missing_data(
    test_client, describe, logged_in, admin_user, watch_signal
):
    with describe('setup'), logged_in(admin_user):
        user_added = watch_signal(
            signals.USER_ADDED_TO_COURSE, clear_all_but=[]
        )
        provider = helpers.create_lti1p3_provider(
            test_client,
            'Canvas',
            iss='https://canvas.instructure.com',
            client_id=str(uuid.uuid4()) + '_lms=' + 'Canvas'
        )

        data = make_launch_data(
            CANVAS_DATA,
            provider,
            {
                'Assignment.id': 'asdf',
                'Course.id': 'asdfs',
            },
        )

        def ensure_fails(data, err_msg):
            _, launch = do_oidc_and_lti_launch(
                test_client, provider, data, 400
            )
            assert err_msg in launch['message']
            assert user_added.was_not_send
            return launch

    with describe('should fail without email'):
        ensure_fails(
            remove_from(data, 'email'), 'requires the email of the user'
        )

    with describe('should fail without nrps'):
        ensure_fails(
            remove_from(data, lti1p3.claims.NAMESROLES),
            'NamesRoles Provisioning service is not enabled'
        )

    with describe('should fail without custom args'):
        ensure_fails(
            remove_from(data, lti1p3.claims.CUSTOM),
            'The LTI launch is missing required custom claims'
        )

    with describe('not fail without email for test student'):
        do_oidc_and_lti_launch(
            test_client,
            provider,
            remove_from(merge(data, {'name': 'Test Student'}), 'email'),
        )
        assert user_added.was_send_once
        assert user_added.signal_arg.user.email == 'test_student@codegra.de'
