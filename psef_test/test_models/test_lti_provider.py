import copy
import uuid

import furl
import pytest
import pylti1p3.names_roles
import pylti1p3.service_connector
import pylti1p3.assignments_grades

import helpers
import psef.models as m
import psef.signals as signals
import psef.lti.v1_3.claims as claims


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
                # Not correct at all, but the function should still not crash.
                'message': object(),
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


def test_delete_submission_passback(
    lti1p3_provider, describe, logged_in, admin_user, watch_signal,
    stub_function, test_client, session, tomorrow
):
    with describe('setup'), logged_in(admin_user):
        watch_signal(signals.WORK_CREATED, clear_all_but=[])
        watch_signal(signals.GRADE_UPDATED, clear_all_but=[])
        watch_signal(signals.USER_ADDED_TO_COURSE, clear_all_but=[])
        stub_function(
            pylti1p3.service_connector.ServiceConnector,
            'get_access_token', lambda: ''
        )
        stub_passback = stub_function(
            pylti1p3.assignments_grades.AssignmentsGradesService, 'put_grade'
        )

        course, course_conn = helpers.create_lti1p3_course(
            test_client, session, lti1p3_provider
        )
        assig = helpers.create_lti1p3_assignment(
            session, course, state='done', deadline=tomorrow
        )
        user = helpers.create_lti1p3_user(session, lti1p3_provider)
        lti_user_id = m.UserLTIProvider.query.filter_by(user=user
                                                        ).one().lti_user_id
        course_conn.maybe_add_user_to_course(user, ['Learner'])

        sub_oldest, sub_older, sub_middle, sub_newest = [
            helpers.to_db_object(
                helpers.create_submission(test_client, assig, for_user=user),
                m.Work
            ) for _ in range(4)
        ]
        signal = watch_signal(
            signals.WORK_DELETED,
            clear_all_but=[m.LTI1p3Provider._delete_submission]
        )

        def do_delete(sub):
            with logged_in(admin_user):
                test_client.req(
                    'delete', f'/api/v1/submissions/{helpers.get_id(sub)}', 204
                )

    with describe('Delete non newest'):
        do_delete(sub_older)
        assert signal.was_send_once
        assert not stub_passback.called

    with describe('Calling method for non existing work simply does nothing'):
        m.LTI1p3Provider._delete_submission(1000000)
        assert not stub_passback.called

    with describe('Calling method for non deleted work does nothing'):
        m.LTI1p3Provider._delete_submission(helpers.get_id(sub_newest))
        assert not stub_passback.called

    with describe('Delete newest should passback grade of new newest'):
        sub_middle.set_grade(5.0, m.User.resolve(admin_user))
        session.commit()
        # We should have removed the grade_updated signal
        assert not stub_passback.called

        do_delete(sub_newest)
        assert signal.was_send_once
        assert stub_passback.called_amount == 1
        grade, = stub_passback.all_args[0].values()
        assert grade.get_score_given() == 5.0
        assert grade.get_user_id() == lti_user_id

    with describe('Deleting new newest should passback next non deleted'):
        sub_older.set_grade(6.0, m.User.resolve(admin_user))
        sub_oldest.set_grade(8.0, m.User.resolve(admin_user))
        session.commit()
        assert not m.GradeHistory.query.filter_by(work=sub_oldest
                                                  ).one().passed_back

        do_delete(sub_middle)
        assert signal.was_send_once
        assert stub_passback.called_amount == 1
        grade, = stub_passback.all_args[0].values()
        # Should passback oldest as we deleted older in an earlier block
        assert grade.get_score_given() == 8.0
        assert grade.get_user_id() == lti_user_id

        # Should update history
        assert m.GradeHistory.query.filter_by(work=sub_oldest
                                              ).one().passed_back

    with describe('Deleting without any existing submission should passback'):
        do_delete(sub_oldest)
        assert signal.was_send_once
        assert stub_passback.called_amount == 1
        grade, = stub_passback.all_args[0].values()
        assert grade.get_score_given() is None
        assert grade.get_grading_progress() == 'NotReady'
        assert grade.get_user_id() == lti_user_id
