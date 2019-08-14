/* SPDX-License-Identifier: AGPL-3.0-only */
import Vue from 'vue';
import axios from 'axios';
import moment from 'moment';

import * as utils from '@/utils';
import { FileTree, Feedback } from '@/models/submission';
import * as types from '../mutation-types';
import { MANAGE_ASSIGNMENT_PERMISSIONS, MANAGE_GENERAL_COURSE_PERMISSIONS } from '../../constants';

const getters = {
    courses: state => state.courses,
    assignments: state => {
        if (!state.courses) return {};

        return Object.values(state.courses).reduce((assignments, course) => {
            course.assignments.forEach(assignment => {
                assignments[assignment.id] = assignment;
            });
            return assignments;
        }, {});
    },
};

const loaders = {
    feedback: {},
    fileTrees: {},
};

function getAssignment(state, assignmentId) {
    const assignment = getters.assignments(state)[assignmentId];

    if (assignment == null) {
        throw ReferenceError(`Could not find assignment: ${assignmentId}`);
    }

    return assignment;
}

const actions = {
    async loadCourses({ state, commit, dispatch }) {
        if (state.currentCourseLoader == null) {
            commit(types.SET_COURSES_PROMISE, dispatch('reloadCourses'));
        }

        return state.currentCourseLoader;
    },

    deleteSubmission({ commit }, { assignmentId, submissionId }) {
        commit(types.DELETE_SUBMISSION, { assignmentId, submissionId });
    },

    addSubmission({ commit }, { assignmentId, submission }) {
        submission.formatted_created_at = utils.readableFormatDate(submission.created_at);
        submission.grade = utils.formatGrade(submission.grade);
        commit(types.ADD_SUBMISSION, { assignmentId, submission });
    },

    setRubric({ commit }, { assignmentId, rubric, maxPoints }) {
        commit(types.UPDATE_ASSIGNMENT, {
            assignmentId,
            assignmentProps: { rubric, fixed_max_rubric_points: maxPoints },
        });
    },

    async forceLoadRubric({ commit }, assignmentId) {
        const rubric = await axios
            .get(`/api/v1/assignments/${assignmentId}/rubrics/`)
            .then(({ data }) => data, () => null);
        commit(types.UPDATE_ASSIGNMENT, {
            assignmentId,
            assignmentProps: { rubric },
        });
    },

    forceLoadSubmissions(context, assignmentId) {
        // This needs to be in one promise to make sure that two very quick
        // calls to `loadSubmissions` still only does one request (for the
        // same arguments of course).
        const promiseFun = async () => {
            await context.dispatch('loadCourses');

            if (context.getters.assignments[assignmentId] == null) {
                return;
            }

            await Promise.all([
                axios.get(`/api/v1/assignments/${assignmentId}/submissions/?extended`).then(
                    ({ data: submissions }) => {
                        submissions.forEach(sub => {
                            sub.formatted_created_at = utils.readableFormatDate(sub.created_at);
                            sub.grade = utils.formatGrade(sub.grade);
                        });
                        return submissions;
                    },
                    () => [],
                ),
                axios
                    .get(`/api/v1/assignments/${assignmentId}/rubrics/`)
                    .then(({ data }) => data, () => null),
                axios
                    .get(`/api/v1/assignments/${assignmentId}/graders/`)
                    .then(({ data }) => data, () => null),
            ]).then(([submissions, rubric, graders]) => {
                context.commit(types.UPDATE_ASSIGNMENT, {
                    assignmentId,
                    assignmentProps: { submissions, rubric, graders },
                });
            });

            // It is possible that in the mean time these promises were
            // cleared. Simply store them again to prevent double loading.
            context.commit(types.SET_SUBMISSIONS_PROMISE, {
                assignmentId,
                promise: Promise.resolve(),
            });
        };

        const promise = promiseFun();
        context.commit(types.SET_SUBMISSIONS_PROMISE, {
            assignmentId,
            promise,
        });

        return promise;
    },

    async loadSubmissions(context, assignmentId) {
        if (context.state.submissionsLoaders[assignmentId] == null) {
            await context.dispatch('forceLoadSubmissions', assignmentId);
        }

        return context.state.submissionsLoaders[assignmentId];
    },

    async loadSubmissionFileTree({ commit, dispatch, state }, { assignmentId, submissionId }) {
        await dispatch('loadSubmissions', assignmentId);

        const submission = getAssignment(state, assignmentId).submissions.find(
            sub => sub.id === submissionId,
        );

        if (submission == null) {
            throw new Error('Failed to load submission');
        }

        if (submission.fileTree != null) {
            return null;
        }

        if (loaders.fileTrees[submissionId] == null) {
            loaders.fileTrees[submissionId] = Promise.all([
                axios.get(`/api/v1/submissions/${submissionId}/files/`),
                axios
                    .get(`/api/v1/submissions/${submissionId}/files/`, {
                        params: { owner: 'teacher' },
                    })
                    .catch(err => {
                        switch (utils.getProps(err, null, 'response', 'status')) {
                            case 403:
                                return { data: null };
                            default:
                                throw err;
                        }
                    }),
            ]).then(
                ([student, teacher]) => {
                    delete loaders.fileTrees[submissionId];
                    commit(types.UPDATE_SUBMISSION, {
                        assignmentId,
                        submissionId,
                        submissionProps: {
                            fileTree: new FileTree(student.data, teacher.data),
                        },
                    });
                },
                err => {
                    delete loaders.fileTrees[submissionId];
                    throw err;
                },
            );
        }

        return loaders.fileTrees[submissionId];
    },

    async loadSubmissionFeedback({ commit, dispatch, state }, { assignmentId, submissionId }) {
        await dispatch('loadSubmissions', assignmentId);

        const submission = getAssignment(state, assignmentId).submissions.find(
            sub => sub.id === submissionId,
        );

        if (submission == null) {
            throw new Error('Failed to load submission');
        }

        if (submission.feedback != null) {
            return null;
        }

        if (loaders.feedback[submissionId] == null) {
            loaders.feedback[submissionId] = axios
                .get(`/api/v1/submissions/${submissionId}/feedbacks/`)
                .then(
                    ({ data }) => {
                        delete loaders.feedback[submissionId];
                        commit(types.UPDATE_SUBMISSION, {
                            assignmentId,
                            submissionId,
                            submissionProps: {
                                feedback: new Feedback(data),
                            },
                        });
                    },
                    err => {
                        delete loaders.feedback[submissionId];

                        switch (utils.getProps(err, null, 'response', 'status')) {
                            case 403:
                                return;
                            default:
                                throw err;
                        }
                    },
                );
        }

        return loaders.feedback[submissionId];
    },

    addSubmissionFeedbackLine(
        { commit, state },
        {
            assignmentId, submissionId, fileId, line, author,
        },
    ) {
        const submission = getAssignment(state, assignmentId).submissions.find(
            sub => sub.id === submissionId,
        );

        if (submission == null || submission.feedback == null) {
            throw new Error('Failed to load submission');
        }

        commit(types.UPDATE_SUBMISSION_FEEDBACK, {
            submission,
            fileId,
            line,
            data: '',
            author,
        });
    },

    submitSubmissionFeedbackLine(
        { commit, state },
        {
            assignmentId, submissionId, fileId, line, data, author,
        },
    ) {
        const submission = getAssignment(state, assignmentId).submissions.find(
            sub => sub.id === submissionId,
        );

        if (submission == null || submission.feedback == null) {
            throw new Error('Failed to load submission');
        }

        return axios.put(`/api/v1/code/${fileId}/comments/${line}`, { comment: data }).then(() =>
            commit(types.UPDATE_SUBMISSION_FEEDBACK, {
                submission,
                fileId,
                line,
                data,
                author,
            }),
        );
    },

    deleteSubmissionFeedbackLine(
        { commit, state },
        {
            assignmentId, submissionId, fileId, line, onServer,
        },
    ) {
        const submission = getAssignment(state, assignmentId).submissions.find(
            sub => sub.id === submissionId,
        );

        if (submission == null || submission.feedback == null) {
            throw new Error('Failed to load submission');
        }

        function cont() {
            commit(types.UPDATE_SUBMISSION_FEEDBACK, {
                submission,
                fileId,
                line,
                data: null,
            });
        }

        if (onServer) {
            return axios.delete(`/api/v1/code/${fileId}/comments/${line}`).then(() => cont);
        } else {
            return Promise.resolve(cont);
        }
    },

    updateSubmission({ commit }, { assignmentId, submissionId, submissionProps }) {
        commit(types.UPDATE_SUBMISSION, {
            assignmentId,
            submissionId,
            submissionProps,
        });
    },

    async reloadCourses({ commit }) {
        let courses;
        let perms;

        try {
            [{ data: courses }, { data: perms }] = await Promise.all([
                axios.get('/api/v1/courses/?extended=true'),
                axios.get('/api/v1/permissions/?type=course'),
            ]);
        } catch (_) {
            return commit(types.CLEAR_COURSES);
        }
        courses.forEach(c => {
            c.permissions = perms[c.id];
        });

        const [manageCourses, manageAssigs, createAssigs] = Object.entries(perms).reduce(
            ([course, assig, create], [key, val]) => {
                assig[key] = Object.entries(val).some(
                    ([k, v]) => MANAGE_ASSIGNMENT_PERMISSIONS.indexOf(k) !== -1 && v,
                );

                course[key] = Object.entries(val).some(
                    ([k, v]) => MANAGE_GENERAL_COURSE_PERMISSIONS.indexOf(k) !== -1 && v,
                );

                create[key] = Object.entries(val).some(
                    ([k, v]) => k === 'can_create_assignment' && v,
                );

                return [course, assig, create];
            },
            [{}, {}, {}],
        );

        return commit(types.SET_COURSES, [
            courses,
            manageCourses,
            manageAssigs,
            createAssigs,
            perms,
        ]);
    },

    updateCourse({ commit }, data) {
        commit(types.UPDATE_COURSE, data);
    },

    updateAssignment({ commit }, data) {
        commit(types.UPDATE_ASSIGNMENT, data);
    },
};

const mutations = {
    [types.SET_COURSES](state, [courses, manageCourses, manageAssigs, createAssigs, perms]) {
        state.submissionsLoaders = {};

        state.courses = courses.reduce((res, course) => {
            course.assignments.forEach(assignment => {
                assignment.course = course;
                assignment.canManage = manageAssigs[course.id];

                // WARNING: This code is complex. If you change it, it will
                // probably be wrong...

                let reminderTime = moment.utc(assignment.reminder_time, moment.ISO_8601).local();
                // This indicates if we got a valid reminder time from the
                // server. We set it to something useful as a default if this is
                // not the case.
                assignment.has_reminder_time = reminderTime.isValid();
                if (!assignment.has_reminder_time) {
                    let baseTime = null;

                    if (assignment.deadline) {
                        baseTime = moment.utc(assignment.deadline, moment.ISO_8601).local();

                        if (!reminderTime.isValid() || reminderTime.isBefore(moment())) {
                            baseTime = moment();
                        }
                    } else {
                        baseTime = moment();
                    }

                    reminderTime = baseTime.clone().add(1, 'weeks');
                }
                assignment.reminder_time = reminderTime.format('YYYY-MM-DDTHH:mm');

                if (assignment.deadline) {
                    assignment.formatted_deadline = utils.readableFormatDate(assignment.deadline);
                    assignment.deadline = utils.formatDate(assignment.deadline);
                } else {
                    assignment.formatted_deadline = null;
                }

                assignment.created_at = utils.formatDate(assignment.created_at);
            });

            course.permissions = perms[course.id];
            course.canManage = manageCourses[course.id];
            course.canCreateAssignments = createAssigs[course.id];

            res[course.id] = course;
            return res;
        }, {});
    },

    [types.CLEAR_COURSES](state) {
        state.courses = {};
        state.currentCourseLoader = null;
        state.submissionsLoaders = {};
    },

    [types.UPDATE_COURSE](state, { courseId, courseProps }) {
        const course = state.courses[courseId];

        if (course == null) {
            throw ReferenceError(`Could not find course: ${courseId}`);
        }

        Object.keys(courseProps).forEach(key => {
            if (!{}.hasOwnProperty.call(course, key) || key === 'id') {
                throw TypeError(`Cannot set course property: ${key}`);
            }

            Vue.set(course, key, courseProps[key]);
        });
    },

    [types.SET_COURSES_PROMISE](state, promise) {
        state.currentCourseLoader = promise;
    },

    [types.SET_SUBMISSIONS_PROMISE](state, { promise, assignmentId }) {
        Vue.set(state.submissionsLoaders, assignmentId, promise);
    },

    [types.UPDATE_ASSIGNMENT](state, { assignmentId, assignmentProps }) {
        const assignment = getAssignment(state, assignmentId);

        Object.keys(assignmentProps).forEach(key => {
            if (
                key !== 'submissions' &&
                key !== 'rubric' &&
                key !== 'graders' &&
                (!{}.hasOwnProperty.call(assignment, key) || key === 'id')
            ) {
                throw TypeError(`Cannot set assignment property: ${key}`);
            }

            Vue.set(assignment, key, assignmentProps[key]);
        });
    },

    [types.ADD_SUBMISSION](state, { assignmentId, submission }) {
        const assignment = getAssignment(state, assignmentId);

        Vue.set(assignment, 'submissions', [submission, ...(assignment.submissions || [])]);
    },

    [types.DELETE_SUBMISSION](state, { assignmentId, submissionId }) {
        const assignment = getAssignment(state, assignmentId);

        if (assignment.submissions != null) {
            Vue.set(
                assignment,
                'submissions',
                assignment.submissions.filter(sub => sub.id !== submissionId),
            );
        }
    },

    [types.UPDATE_SUBMISSION](state, { assignmentId, submissionId, submissionProps }) {
        const assignment = getAssignment(state, assignmentId);

        const submission = assignment.submissions.find(s => s.id === submissionId);
        if (submission == null) {
            throw ReferenceError('Submission not found');
        }

        Object.entries(submissionProps).forEach(([key, val]) => {
            if (key === 'id') {
                throw TypeError(`Cannot set submission property: ${key}`);
            }

            Vue.set(submission, key, key === 'grade' ? utils.formatGrade(val) : val);
        });
    },

    [types.UPDATE_SUBMISSION_FEEDBACK](state, {
        submission, fileId, line, data, author,
    }) {
        const feedback = submission.feedback;
        const fileFeedback = feedback.user[fileId] || {};

        if (data == null) {
            Vue.delete(fileFeedback, line);
            if (Object.keys(fileFeedback).length === 0) {
                Vue.delete(feedback.user, fileId);
            }
        } else {
            const lineFeedback = fileFeedback[line] || { line, author };
            Vue.set(
                fileFeedback,
                line,
                Object.assign({}, lineFeedback, {
                    msg: data,
                }),
            );
            Vue.set(feedback.user, fileId, Object.assign({}, fileFeedback));
        }

        Vue.set(feedback, 'user', Object.assign({}, feedback.user));
        Vue.set(submission, 'feedback', feedback);
    },
};

export default {
    namespaced: true,
    state: {
        courses: {},
        currentCourseLoader: null,
        submissionsLoaders: {},
    },

    getters,
    actions,
    mutations,
};
