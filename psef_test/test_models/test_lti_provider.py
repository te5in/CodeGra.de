import furl

import helpers
import psef.models as m


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
