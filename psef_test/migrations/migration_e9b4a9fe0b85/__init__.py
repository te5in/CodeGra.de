import subprocess
from itertools import groupby

import pytest


def test_connections(conn_by_id, new_style_courses, old_style_courses):
    for cur_course, old_course in zip(new_style_courses, old_style_courses):
        assert cur_course.id == old_course.id
        if old_course.lti_provider_id is None:
            assert cur_course.id not in conn_by_id
        else:
            assert cur_course.id in conn_by_id
            conn = conn_by_id[cur_course.id]
            assert conn.id is not None
            assert conn.lti_provider_id == old_course.lti_provider_id
            assert conn.lti_course_id == old_course.lti_course_id
            assert conn.deployment_id == old_course.lti_course_id


class UpgradeTester:
    def __init__(self, db, **_):
        self.db = db
        self.courses = None

    def get_courses(self):
        return self.db.engine.execute('SELECT * FROM "Course" ORDER BY id'
                                      ).fetchall()

    @staticmethod
    def do_test():
        return True

    def load_data(self):
        self.courses = self.get_courses()

    def check_upgrade(self):
        cur_courses = self.get_courses()
        assert len(cur_courses) > 0
        assert len(self.courses
                   ) == len(cur_courses), 'No courses should be deleted'

        connections = self.db.engine.execute(
            'SELECT * FROM course_lti_provider ORDER BY course_id'
        ).fetchall()
        assert len(set(c.course_id for c in connections)) == len(connections)
        conn_by_id = {c.course_id: c for c in connections}
        test_connections(conn_by_id, cur_courses, self.courses)


class DowngradeTester:
    def __init__(self, db, **_):
        self.db = db
        self.courses = None
        self.conn_by_id = None

    def get_courses(self):
        return self.db.engine.execute('SELECT * FROM "Course" ORDER BY id'
                                      ).fetchall()

    @staticmethod
    def do_test():
        return True

    def load_data(self):
        self.courses = self.get_courses()
        connections = self.db.engine.execute(
            'SELECT * FROM course_lti_provider ORDER BY course_id'
        ).fetchall()
        assert len(set(c.course_id for c in connections)) == len(connections)
        self.conn_by_id = {c.course_id: c for c in connections}

    def check_downgrade(self):
        cur_courses = self.get_courses()
        assert len(cur_courses) > 0
        assert len(self.courses
                   ) == len(cur_courses), 'No courses should be deleted'

        test_connections(self.conn_by_id, self.courses, cur_courses)
