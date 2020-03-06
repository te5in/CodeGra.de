import os
from datetime import datetime, timedelta

from freezegun import freeze_time

import psef
import helpers


def test_proxy_with_submission(
    test_client, logged_in, describe, session, admin_user
):
    with describe('setup'), logged_in(admin_user):
        course = helpers.create_course(test_client)
        assig = helpers.create_assignment(
            test_client, course, state='open', deadline='tomorrow'
        )
        stud = helpers.create_user_with_role(session, 'Student', [course])
        stud2 = helpers.create_user_with_role(session, 'Student', [course])

        sub_data = (
            (
                f'{os.path.dirname(__file__)}/../test_data/test_submissions/'
                'html.tar.gz'
            ),
            'f.tar.gz',
        )
        s1 = helpers.create_submission(
            test_client, assig, submission_data=sub_data, for_user=stud
        )['id']
        s2 = helpers.create_submission(
            test_client, assig, submission_data=sub_data, for_user=stud2
        )['id']

        data = {
            'allow_remote_resources': True,
            'allow_remote_scripts': True,
            'teacher_revision': False,
        }

    with describe('Students can only create proxy when they may see files'
                  ), logged_in(stud):
        test_client.req(
            'post', f'/api/v1/submissions/{s1}/proxy', 200, data=data
        )
        test_client.req(
            'post', f'/api/v1/submissions/{s2}/proxy', 403, data=data
        )

        # Student has no permission for teacher files
        data['teacher_revision'] = True
        test_client.req(
            'post', f'/api/v1/submissions/{s1}/proxy', 403, data=data
        )
        data['teacher_revision'] = False

    with describe('remote_scripts and remote_resources connection'
                  ), logged_in(stud):
        data['allow_remote_resources'] = False
        err = test_client.req(
            'post', f'/api/v1/submissions/{s1}/proxy', 400, data=data
        )
        assert 'The value "allow_remote_scripts" can only be true' in err[
            'message']


def test_getting_files_from_proxy(
    test_client, logged_in, describe, session, admin_user, monkeypatch
):
    with describe('setup'), logged_in(admin_user):
        course = helpers.create_course(test_client)
        assig = helpers.create_assignment(
            test_client, course, state='open', deadline='tomorrow'
        )
        stud = helpers.create_user_with_role(session, 'Student', [course])

        sub_data = (
            (
                f'{os.path.dirname(__file__)}/../test_data/test_submissions/'
                'html.tar.gz'
            ),
            'f.tar.gz',
        )
        s1 = helpers.create_submission(
            test_client, assig, submission_data=sub_data, for_user=stud
        )['id']

    with describe('Proxy allows views without active user'):
        with logged_in(stud):
            proxy = test_client.req(
                'post',
                f'/api/v1/submissions/{s1}/proxy',
                200,
                data={
                    'allow_remote_resources': True,
                    'allow_remote_scripts': True,
                    'teacher_revision': False,
                }
            )['id']

        res = test_client.post(
            f'/api/v1/proxies/{proxy}/nested/index.html',
            follow_redirects=False
        )
        assert res.status_code == 303
        res = test_client.get(res.headers['Location'])
        assert res.headers['Content-Type'] == 'text/html; charset=utf-8'
        assert res.headers[
            'Content-Security-Policy'
        ] == "default-src * data: 'unsafe-eval' 'unsafe-inline'"

    with describe('Proxy should have correct content type'):
        res = test_client.get(f'/api/v1/proxies/fiets.jpg')
        assert res.status_code == 200
        assert res.headers['Content-Type'] == 'image/jpeg'

    with describe('Not found files should return a 404'):
        for f in ['nope', 'non_existing_dir/file', 'nested/nope']:
            res = test_client.get(f'/api/v1/proxies/{f}')
            assert res.status_code == 404

    with describe('A directory will try to retrieve the index.html'):
        res1 = test_client.get(f'/api/v1/proxies/nested/index.html')
        assert res1.status_code == 200

        res2 = test_client.get(f'/api/v1/proxies/nested')
        assert res2.status_code == 200

        res3 = test_client.get(f'/api/v1/proxies/nested')
        assert res3.status_code == 200

        assert len(res1.get_data()) > 1
        assert res1.get_data() == res2.get_data()
        assert res1.get_data() == res3.get_data()

    with describe('A path is required'):
        res = test_client.get(f'/api/v1/proxies/')
        assert res.status_code == 404

    with describe('When we find a dir 404 is returned'):
        monkeypatch.setattr(
            psef.v1.proxies, '_INDEX_FILES', ['not_in_dir.html']
        )
        res = test_client.get(f'/api/v1/proxies/nested')
        assert res.status_code == 404

    with describe('A proxy should stop working when expired'):
        url = f'/api/v1/proxies/fiets.jpg'
        assert test_client.get(url).status_code == 200

        with freeze_time(datetime.utcnow() + timedelta(days=1)):
            assert test_client.get(url).status_code == 400

    with describe('A proxy cannot be used when the stat is deleted'):
        url = f'/api/v1/proxies/fiets.jpg'
        assert test_client.get(url).status_code == 200

        psef.models.Proxy.query.filter_by(id=proxy).update({
            'state': psef.models.ProxyState.deleted,
        })
        assert test_client.get(url).status_code == 404

        psef.models.Proxy.query.filter_by(id=proxy).update({
            'state': psef.models.ProxyState.in_use,
        })
        assert test_client.get(url).status_code == 200

    with describe('We cannot reused the proxy'):
        assert test_client.get('/api/v1/proxies/fiets.jpg').status_code == 200
        assert test_client.get(
            f'/api/v1/proxies/{proxy}/fiets.jpg'
        ).status_code == 200

        # After clearing cookies we cannot use the endpoint anymore
        test_client.cookie_jar.clear()
        assert test_client.get('/api/v1/proxies/fiets.jpg').status_code == 400
        assert test_client.get(
            f'/api/v1/proxies/{proxy}/fiets.jpg'
        ).status_code == 400

        # Cannot do a new post to the proxy endpoint
        res = test_client.post(
            f'/api/v1/proxies/{proxy}/nested/index.html',
            follow_redirects=True
        )
        assert res.status_code == 404
        assert test_client.get('/api/v1/proxies/fiets.jpg').status_code == 400


def test_teacher_revision_in_proxy(
    test_client, logged_in, describe, session, admin_user, app
):
    with describe('setup'), logged_in(admin_user):
        course = helpers.create_course(test_client)
        assig = helpers.create_assignment(
            test_client, course, state='done', deadline='tomorrow'
        )
        stud = helpers.create_user_with_role(session, 'Student', [course])

        sub_data = (
            (
                f'{os.path.dirname(__file__)}/../test_data/test_submissions/'
                'html.tar.gz'
            ),
            'f.tar.gz',
        )
        s1 = helpers.create_submission(
            test_client, assig, submission_data=sub_data, for_user=stud
        )['id']
        files = test_client.req(
            'get',
            f'/api/v1/submissions/{s1}/files/',
            200,
        )

        # Get the file nested/index.html
        student_file_id = [
            n['id'] for f in files['entries'] for n in f.get('entries', [])
            if f['name'] == 'nested' and n['name'] == 'index.html'
        ][0]

        test_client.req(
            'patch',
            f'/api/v1/code/{student_file_id}',
            200,
            real_data='TEACHER FILE',
        )
        test_client.req(
            'post',
            f'/api/v1/submissions/{s1}/files/?path=f.tar.gz/nested/woo',
            200,
        )

        student_proxy = test_client.req(
            'post',
            f'/api/v1/submissions/{s1}/proxy',
            200,
            data={
                'allow_remote_resources': True,
                'allow_remote_scripts': True,
                'teacher_revision': False,
            }
        )['id']
        teacher_proxy = test_client.req(
            'post',
            f'/api/v1/submissions/{s1}/proxy',
            200,
            data={
                'allow_remote_resources': True,
                'allow_remote_scripts': True,
                'teacher_revision': True,
            }
        )['id']

    with describe(
        'Teacher revision proxy should return teacher rev'
    ), app.test_client() as t_client, app.test_client() as s_client:
        res = t_client.post(
            f'/api/v1/proxies/{teacher_proxy}/nested/index.html',
            follow_redirects=True
        )
        assert res.status_code == 200
        assert res.get_data() == b'TEACHER FILE'

        res = s_client.post(
            f'/api/v1/proxies/{student_proxy}/nested/index.html',
            follow_redirects=True
        )
        assert res.status_code == 200
        assert res.get_data() != b'TEACHER FILE'

        res = t_client.get(f'/api/v1/proxies/nested/woo')
        assert res.status_code == 200
        assert res.get_data() == b''

        res = s_client.get(f'/api/v1/proxies/nested/woo')
        assert res.status_code == 404
