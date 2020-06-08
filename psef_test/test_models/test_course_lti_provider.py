import pylti1p3.names_roles

import helpers
import psef.models as m
import psef.signals as signals


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


def test_maybe_add_user_to_course(
    describe, lti1p3_provider, test_client, admin_user, logged_in, session,
    watch_signal
):
    with describe('setup'), logged_in(admin_user):
        course, conn = helpers.create_lti1p3_course(
            test_client, session, lti1p3_provider
        )
        signal = watch_signal(signals.USER_ADDED_TO_COURSE, clear_all_but=[])
        user = helpers.create_user_with_role(session, 'Teacher', [])
        user2 = helpers.create_user_with_role(session, 'Teacher', [])
        user3 = helpers.create_user_with_role(session, 'Teacher', [])
        user4 = helpers.create_user_with_role(session, 'Teacher', [])
        user5 = helpers.create_user_with_role(session, 'Teacher', [])
        student_role = m.CourseRole.query.filter_by(
            name='Student', course=course
        ).one()
        assert student_role is not None

    with describe('adding user without roles claim always creates a new role'):
        conn.maybe_add_user_to_course(user, [])
        assert signal.was_send_once
        assert user.is_enrolled(course)
        assert user.courses[course.id].name == 'New LTI Role'

        signal.reset()
        conn.maybe_add_user_to_course(user2, [])
        assert signal.was_send_once
        assert user2.is_enrolled(course)
        assert user2.courses[course.id].name == 'New LTI Role (1)'
        assert user2.courses[course.id].id != user.courses[course.id].id

    with describe('user already in course does nothing'):
        conn.maybe_add_user_to_course(user, ['Learner'])
        assert signal.was_not_send
        assert user.courses[course.id].name == 'New LTI Role'

    with describe('adding user with known role uses that role'):
        conn.maybe_add_user_to_course(user3, ['Learner'])
        assert signal.was_send_once
        assert user3.is_enrolled(course)
        assert user3.courses[course.id].id == student_role.id

    with describe(
        'Using unmapped role creates a new role if it does not exist'
    ):
        conn.maybe_add_user_to_course(user4, ['Student', 'Other role'])
        assert signal.was_send_once
        assert user4.is_enrolled(course)
        assert user4.courses[course.id].name == 'Unmapped LTI Role (Student)'

        signal.reset()
        conn.maybe_add_user_to_course(user5, ['Other role', 'Student'])
        assert signal.was_send_once
        assert user5.is_enrolled(course)
        assert user5.courses[course.id].name == 'Unmapped LTI Role (Student)'
