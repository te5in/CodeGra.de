from psef import models as m
from psef.models.user import User
from psef.permissions import CoursePermission, GlobalPermission


def test_user_has_permission():
    user_without_role = User('', '', '', '', active=True)
    assert not user_without_role.has_permission(
        GlobalPermission.can_edit_own_password
    )
    assert not user_without_role.has_permission(
        CoursePermission.can_submit_own_work, course_id=1
    )


def test_user_is_enrolled():
    user = User('', '', '', '', active=True)
    assert not user.virtual
    course = m.Course(id=5)
    crole = m.CourseRole(name='Hello', course=course, hidden=False)

    assert not user.is_enrolled(course)
    assert not user.is_enrolled(5)

    user.enroll_in_course(course_role=crole)

    assert course.id in user.courses
    assert user.is_enrolled(course)
    assert user.is_enrolled(5)
    assert not user.is_enrolled(6)

    user.virtual = True
    # Virtual users are never enrolled
    assert not user.is_enrolled(course)
    assert not user.is_enrolled(5)
    # But the connection still exists
    assert course.id in user.courses
