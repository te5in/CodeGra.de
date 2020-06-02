import copy
import uuid

import furl
import pytest
import pylti1p3.names_roles

import helpers
import psef.models as m
import psef.signals as signals
import psef.lti.v1_3.claims as claims


@pytest.fixture
def lti1p3_provider(logged_in, admin_user, test_client):
    with logged_in(admin_user):
        prov = helpers.to_db_object(
            helpers.create_lti1p3_provider(test_client, 'Canvas'),
            m.LTI1p3Provider
        )
    yield prov


def test_get_self_from_course(
    describe, admin_user, test_client, session, app, logged_in
):
    with describe('setup'), logged_in(admin_user):
        course = helpers.to_db_object(
            helpers.create_course(test_client), m.Course
        )
        lti_course = helpers.to_db_object(
            helpers.create_lti_course(session, app, admin_user), m.Course
        )

    with describe('Getting without course should return none'):
        assert m.LTI1p1Provider._get_self_from_course(None) is None

    with describe('Getting for non LTI course should return none'):
        assert m.LTI1p1Provider._get_self_from_course(course) is None

    with describe('Getting with LTI course should return instance'):
        prov = m.LTI1p1Provider._get_self_from_course(lti_course)
        assert prov is not None
        assert lti_course.lti_provider.id == prov.id

    with describe('Getting for for other LTI class should return none'):
        assert m.LTI1p3Provider._get_self_from_course(lti_course) is None


def test_get_launch_url(describe, logged_in, admin_user, test_client):
    with describe('setup'), logged_in(admin_user):
        canvas_prov = helpers.to_db_object(
            helpers.create_lti1p3_provider(test_client, 'Canvas'),
            m.LTI1p3Provider
        )
        moodle_prov = helpers.to_db_object(
            helpers.create_lti1p3_provider(test_client, 'Moodle'),
            m.LTI1p3Provider
        )

    with describe('Should return a furl object'):
        # Furl is not typed yet so it makes sense to check this as mypy sees it
        # as an `Any`
        url = canvas_prov.get_launch_url(goto_latest_sub=False)
        assert isinstance(url, furl.furl)

    with describe('should not include an ID for canvas'):
        url = canvas_prov.get_launch_url(goto_latest_sub=False)
        assert canvas_prov.id not in str(url)

    with describe('should not include an ID for moodle'):
        url = moodle_prov.get_launch_url(goto_latest_sub=False)
        assert moodle_prov.id in str(url)

    with describe('should be possible to launch to the latest submission'):
        url = canvas_prov.get_launch_url(goto_latest_sub=True)
        assert '/launch_to_latest_submission' in str(url)


def test_retrieve_users_in_course(
    describe, lti1p3_provider, stub_function_class, monkeypatch, test_client,
    admin_user, logged_in, session, app, watch_signal
):
    with describe('setup'), logged_in(admin_user):
        course = helpers.to_db_object(
            helpers.create_course(test_client), m.Course
        )
        membership_url = f'http://{uuid.uuid4()}'
        lti_course, _ = helpers.create_lti1p3_course(
            test_client,
            session,
            lti1p3_provider,
            membership_url,
        )
        return_value = []

        stub_get = stub_function_class(lambda: copy.deepcopy(return_value))
        monkeypatch.setattr(
            pylti1p3.names_roles.NamesRolesProvisioningService, 'get_members',
            stub_get
        )

        assig_created_signal = watch_signal(
            # Make sure we flush the db as we expect that the created
            # assignment can be found by doing queries.
            signals.ASSIGNMENT_CREATED,
            flush_db=True
        )
        user_added_signal = watch_signal(
            signals.USER_ADDED_TO_COURSE,
            clear_all_but=[m.LTI1p3Provider._retrieve_users_in_course]
        )

        new_user_id1 = str(uuid.uuid4())
        new_user_id2 = str(uuid.uuid4())

        do_poll_again = True
        stub_poll_again = stub_function_class(lambda: do_poll_again)
        monkeypatch.setattr(
            m.CourseLTIProvider, 'can_poll_names_again', stub_poll_again
        )

    with describe('make sure it is connected to the necessary signals'):
        assert signals.USER_ADDED_TO_COURSE.is_connected(
            m.LTI1p3Provider._retrieve_users_in_course
        )
        assert signals.ASSIGNMENT_CREATED.is_connected(
            m.LTI1p3Provider._retrieve_users_in_course
        )

    with describe('non lti courses should be ignored'):
        m.LTI1p3Provider._retrieve_users_in_course(course.id)
        assert not stub_get.called

    with describe('should work when no members are returned'):
        assig = helpers.create_lti1p3_assignment(session, lti_course)
        assert assig_created_signal.was_send_once
        assert stub_get.called
        assert user_added_signal.was_not_send
        assert stub_poll_again.called

    with describe('Should be possible to add members'):
        return_value = [
            {
                'status': 'Active',
                'message': {},
                'user_id': new_user_id1,
                'email': 'hello@codegrade.com',
                'name': 'USER1',
            },
            {
                'status': 'Active',
                'message': {
                    claims.CUSTOM: {'cg_username_0': 'username_user2'}
                },
                'user_id': new_user_id2,
                'email': 'hello2@codegrade.com',
                'name': 'USER2',
                'roles': ['Student'],
            },
        ]
        signals.ASSIGNMENT_CREATED.send(assig)
        assert stub_poll_again.called
        assert user_added_signal.was_send_once

        # USER1 should not be added and recursion should not happen
        assert user_added_signal.called_amount == 1
        assert m.User.query.filter_by(username='username_user2'
                                      ).one().is_enrolled(lti_course)
        assert m.User.query.filter_by(email='hello@codegrade.com'
                                      ).one_or_none() is None

    with describe('Can add known users to new courses, even without username'):
        # Remove the message claim
        return_value = [{**r, 'message': {}} for r in return_value]

        with logged_in(admin_user):
            lti_course2, _ = helpers.create_lti1p3_course(
                test_client, session, lti1p3_provider
            )

        helpers.create_lti1p3_assignment(session, lti_course2)

        assert user_added_signal.was_send_once
        assert m.User.query.filter_by(username='username_user2'
                                      ).one().is_enrolled(lti_course2)
        assert m.User.query.filter_by(email='hello@codegrade.com'
                                      ).one_or_none() is None

    with describe('if can poll return no poll should be done'):
        do_poll_again = False
        signals.ASSIGNMENT_CREATED.send(assig)
        assert not stub_get.called


def test_can_poll_names_again(
    describe, lti1p3_provider, test_client, admin_user, logged_in, session,
    watch_signal, monkeypatch, stub_function_class
):
    with describe('setup'), logged_in(admin_user):
        # Disable signal
        watch_signal(signals.ASSIGNMENT_CREATED, clear_all_but=[])
        course, course_lti = helpers.create_lti1p3_course(
            test_client, session, lti1p3_provider
        )
        helpers.create_lti1p3_assignment(session, course)
        stub_get = stub_function_class(lambda: [])
        monkeypatch.setattr(
            pylti1p3.names_roles.NamesRolesProvisioningService, 'get_members',
            stub_get
        )

    with describe('can poll if we never polled'):
        assert course_lti.can_poll_names_again()

    with describe('calling get_members updates last poll date'):
        assert course_lti.last_names_roles_poll is None
        course_lti.get_members(object())
        assert course_lti.last_names_roles_poll is not None

    with describe('now we cannot poll again as we just did that'):
        assert not course_lti.can_poll_names_again()
