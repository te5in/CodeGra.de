import pytest

import helpers
import psef.models as m


def get_all_connections(assignment, amount):
    assig_id = helpers.get_id(assignment)
    assignment = m.Assignment.query.get(assig_id)
    assert assignment is not None, 'Could not find assignment'
    pf_settings = assignment.peer_feedback_settings
    assert pf_settings is not None, 'Not a PF assig'
    connections = sorted((conn.peer_user_id, conn.user_id)
                         for conn in pf_settings.connections)
    seen_amount = {}
    res = {}
    for a, b in connections:
        assert a != b
        if a not in res:
            res[a] = []
        if b not in seen_amount:
            seen_amount[b] = 0
        seen_amount[b] += 1
        assert b not in res[a]
        res[a].append(b)

    for a, conns in res.items():
        assert len(conns) == amount
        assert seen_amount[a] == amount

    return res


@pytest.mark.parametrize('iteration', range(5))
def test_division(
    test_client, admin_user, session, describe, logged_in, yesterday, iteration
):
    with describe('setup'), logged_in(admin_user):
        course = helpers.create_course(test_client)
        assignment = helpers.create_assignment(
            test_client, course, deadline=yesterday
        )
        helpers.enable_peer_feedback(test_client, assignment)
        user1, user2, user3, user4 = [
            helpers.get_id(
                helpers.create_user_with_role(session, 'Student', course)
            ) for _ in range(4)
        ]

    with describe('Single submission no connections'), logged_in(admin_user):
        assert get_all_connections(assignment, 1) == {}
        helpers.create_submission(test_client, assignment, for_user=user1)
        assert get_all_connections(assignment, 1) == {}

    with describe('Second submission does initial division'
                  ), logged_in(admin_user):
        helpers.create_submission(test_client, assignment, for_user=user2)
        assert get_all_connections(assignment,
                                   1) == {user1: [user2], user2: [user1]}

    with describe('Third submission also gets divided'), logged_in(admin_user):
        helpers.create_submission(test_client, assignment, for_user=user3)
        connections = get_all_connections(assignment, 1)
        assert len(connections) == 3
        if connections[user3] == [user1]:
            assert connections[user2] == [user3]
            assert connections[user1] == [user2]
        else:
            assert connections[user3] == [user2]
            assert connections[user1] == [user3]
            assert connections[user2] == [user1]

    with describe('Submitting again does not change division'
                  ), logged_in(admin_user):
        old_connections = get_all_connections(assignment, 1)
        for _ in range(10):
            last_sub3 = helpers.create_submission(
                test_client, assignment, for_user=user3
            )
            assert get_all_connections(assignment, 1) == old_connections

    with describe('Deleting not last submission does not change division'
                  ), logged_in(admin_user):
        old_connections = get_all_connections(assignment, 1)
        _, rv = test_client.req(
            'delete',
            f'/api/v1/submissions/{helpers.get_id(last_sub3)}',
            204,
            include_response=True,
        )
        assert 'warning' not in rv.headers
        assert get_all_connections(assignment, 1) == old_connections

    with describe('Test submission does not change anything'
                  ), logged_in(admin_user):
        old_connections = get_all_connections(assignment, 1)
        for _ in range(10):
            helpers.create_submission(
                test_client, assignment, is_test_submission=True
            )
            assert get_all_connections(assignment, 1) == old_connections

    with describe('user gets assigned to different user every time'
                  ), logged_in(admin_user):
        conns = set()
        for _ in range(20):
            sub = helpers.create_submission(
                test_client, assignment, for_user=user4
            )
            new_conns = get_all_connections(assignment, 1)[user4]
            conns.add(new_conns[0])
            _, rv = test_client.req(
                'delete',
                f'/api/v1/submissions/{helpers.get_id(sub)}',
                204,
                include_response=True,
            )
            assert 'warning' not in rv.headers
        assert len(conns) == 3


@pytest.mark.parametrize('students', [5, 6, 7, 10, 25, 30, 100, 300])
def test_division_larger_assignment(
    test_client, admin_user, session, describe, logged_in, yesterday, students
):
    with describe('setup'), logged_in(admin_user):
        course = helpers.create_course(test_client)
        assignment = helpers.create_assignment(
            test_client, course, deadline=yesterday
        )
        all_users = [
            helpers.get_id(
                helpers.create_user_with_role(session, 'Student', course)
            ) for _ in range(students)
        ]
        user1, *rest_users = all_users
        rest_subs = [(
            user,
            helpers.create_submission(test_client, assignment, for_user=user)
        ) for user in rest_users]

    with describe('Enabling peer feedback should do divide'
                  ), logged_in(admin_user):
        helpers.enable_peer_feedback(test_client, assignment, amount=3)
        conns = get_all_connections(assignment, 3)
        assert len(conns) == len(rest_users)

    with describe('Submitting should still be possible'
                  ), logged_in(admin_user):
        helpers.create_submission(test_client, assignment, for_user=user1)
        conns = get_all_connections(assignment, 3)
        assert len(conns) == len(all_users)
        assert len(conns[user1]) == 3

    with describe('Can delete all rest users'), logged_in(admin_user):
        warning_amount = 0
        for idx, (user_id, sub) in enumerate(rest_subs):
            _, rv = test_client.req(
                'delete',
                f'/api/v1/submissions/{helpers.get_id(sub)}',
                204,
                include_response=True,
            )
            had_warning = 'warning' in rv.headers
            if had_warning:
                warning_amount += 1
            print('Deleting submission of', user_id, 'warning:', had_warning)
            conns = get_all_connections(assignment, 3)
            left = len(all_users) - (idx + 1)
            if left > 3:
                assert len(conns) == left, f'Got wrong amount of conns {conns}'
            else:
                assert len(conns) == 0, f'Got wrong amount of conns {conns}'

        assert warning_amount < len(all_users)


def test_delete_sub_with_cycle(
    test_client, admin_user, session, describe, logged_in, yesterday
):
    with describe('setup'), logged_in(admin_user):
        course = helpers.create_course(test_client)
        assignment = helpers.create_assignment(
            test_client, course, deadline=yesterday
        )
        users = [
            helpers.get_id(
                helpers.create_user_with_role(session, 'Student', course)
            ) for _ in range(5)
        ]
        user1, user2, user3, user4, user5 = users
        subs = {
            user: helpers.create_submission(
                test_client,
                assignment,
                for_user=user,
            )
            for user in users
        }
        helpers.enable_peer_feedback(test_client, assignment, amount=1)

    with describe('setup cycle'):
        assig_id = helpers.get_id(assignment)
        assignment = m.Assignment.query.get(assig_id)
        assert assignment is not None, 'Could not find assignment'
        pf_settings = assignment.peer_feedback_settings
        pf_settings.connections = []

        for reviewer, subject in [
            (user1, user2),
            (user2, user1),
            (user3, user4),
            (user4, user5),
            (user5, user3),
        ]:
            reviewer = m.User.query.get(reviewer)
            subject = m.User.query.get(subject)
            m.AssignmentPeerFeedbackConnection(
                pf_settings, user=subject, peer_user=reviewer
            )

        session.commit()

        # Make sure the just setup connections are valid
        get_all_connections(assignment, 1)

    with describe('delete sub of user in small cycle'), logged_in(admin_user):
        _, rv = test_client.req(
            'delete',
            f'/api/v1/submissions/{helpers.get_id(subs[user2])}',
            204,
            include_response=True,
        )
        assert (
            'All connections for peer feedback were redivided because of this'
            ' deletion.'
        ) in rv.headers['warning']

        conns = get_all_connections(assignment, 1)
        assert set(conns[user1]) & {user3, user4, user5}
