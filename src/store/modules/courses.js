/* SPDX-License-Identifier: AGPL-3.0-only */
import Vue from 'vue';
import axios from 'axios';
import moment from 'moment';

import * as utils from '@/utils';
import { Rubric } from '@/models/rubric';

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
    rubrics: {},
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

    setRubric({ commit }, { assignmentId, rubric, maxPoints }) {
        commit(types.UPDATE_ASSIGNMENT, {
            assignmentId,
            assignmentProps: { rubric, fixed_max_rubric_points: maxPoints },
        });
    },

    async forceLoadGraders({ commit }, assignmentId) {
        const graders = await axios
            .get(`/api/v1/assignments/${assignmentId}/graders/`)
            .then(({ data }) => data, () => null);
        commit(types.UPDATE_ASSIGNMENT, {
            assignmentId,
            assignmentProps: { graders },
        });
    },

    async loadRubric(context, assignmentId) {
        await context.dispatch('loadCourses');

        const assig = context.getters.assignments[assignmentId];
        if (assig.rubric) {
            return;
        }

        await context.dispatch('forceLoadRubric', assignmentId);
    },

    forceLoadRubric({ commit }, assignmentId) {
        if (!loaders.rubrics[assignmentId]) {
            loaders.rubrics[assignmentId] = new Promise(async resolve => {
                const rubric = await axios
                    .get(`/api/v1/assignments/${assignmentId}/rubrics/`)
                    .then(({ data }) => data, () => null);
                commit(types.UPDATE_ASSIGNMENT, {
                    assignmentId,
                    assignmentProps: { rubric },
                });
                delete loaders.rubrics[assignmentId];
                resolve();
            });
        }

        return loaders.rubrics[assignmentId];
    },

    async reloadCourses({ commit }) {
        let courses;
        let perms;
        await commit(`submissions/${types.CLEAR_SUBMISSIONS}`, null, { root: true });

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
                const entries = Object.entries(val);

                assig[key] = entries.some(
                    ([k, v]) => MANAGE_ASSIGNMENT_PERMISSIONS.indexOf(k) !== -1 && v,
                );

                course[key] = entries.some(
                    ([k, v]) => MANAGE_GENERAL_COURSE_PERMISSIONS.indexOf(k) !== -1 && v,
                );

                create[key] = entries.some(([k, v]) => k === 'can_create_assignment' && v);

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
            course.canManageAssignments = manageAssigs[course.id];
            course.canCreateAssignments = createAssigs[course.id];

            Object.defineProperty(course, 'isStudent', {
                get() {
                    return !(
                        this.canManage ||
                        this.canManageAssignments ||
                        this.canCreateAssignments
                    );
                },
            });

            res[course.id] = course;
            return res;
        }, {});
    },

    [types.CLEAR_COURSES](state) {
        state.courses = {};
        state.currentCourseLoader = null;
        loaders.rubrics = {};
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

    [types.UPDATE_ASSIGNMENT](state, { assignmentId, assignmentProps }) {
        const assignment = getAssignment(state, assignmentId);
        let sawRubric = false;

        Object.keys(assignmentProps).forEach(key => {
            if (
                key !== 'rubric' &&
                key !== 'graders' &&
                (!{}.hasOwnProperty.call(assignment, key) || key === 'id')
            ) {
                throw TypeError(`Cannot set assignment property: ${key}`);
            }

            sawRubric = sawRubric || key === 'rubric';
            Vue.set(assignment, key, assignmentProps[key]);
        });
        if (sawRubric) {
            Vue.set(assignment, 'rubricModel', new Rubric(assignmentProps.rubric, assignment));
        }
    },
};

export default {
    namespaced: true,
    state: {
        courses: {},
        currentCourseLoader: null,
    },

    getters,
    actions,
    mutations,
};
