/* SPDX-License-Identifier: AGPL-3.0-only */
import Vue from 'vue';
import axios from 'axios';

import * as utils from '@/utils';
import { sortSubmissions } from '@/utils/FilterSubmissionsManager';
import { FileTree, Feedback } from '@/models/submission';
import * as types from '../mutation-types';

function getSubmission(state, assignmentId, submissionId, throwNotFound = true) {
    const subs = state.submissions[assignmentId];

    let submission = null;
    if (subs != null) {
        submission = subs.find(sub => sub.id === submissionId);
    }

    if (submission == null) {
        if (throwNotFound) {
            throw ReferenceError(
                `Could not find submission: ${submissionId} for assignment ${assignmentId}`,
            );
        }
        return null;
    }

    return submission;
}

const getters = {
    getAllSubmissions: state => assignmentId => state.submissions[assignmentId] || [],
    getSingleSubmission: state => (assignmentId, submissionId) =>
        getSubmission(state, assignmentId, submissionId, false),
    allSubmissions: state => state.submissions,
    latestSubmissions: state => state.latestSubmissions,
    usersWithGroupSubmission: state => state.groupSubmissionUsers,
};

const loaders = {
    feedback: {},
    fileTrees: {},
};

function getUsersInGroup(subs) {
    const userIds = {};
    subs.forEach(sub => {
        if (sub.user.group) {
            sub.user.group.members.forEach(member => {
                userIds[member.id] = sub.user;
            });
        }
    });
    return userIds;
}

function addToLatest(latestSubs, newSub) {
    const len = latestSubs.length;
    let i = 0;
    for (; i < len; ++i) {
        const cur = latestSubs[i];
        if (cur.user.id === newSub.user.id) {
            // Need <= here because we may want to update the same submission,
            // for example when the grade changes.
            if (cur.created_at <= newSub.created_at) {
                Vue.set(latestSubs, i, Object.assign({}, latestSubs[i], newSub));
            }
            break;
        }
    }
    if (i === len) {
        latestSubs.push(newSub);
    }

    return latestSubs;
}

function getLatestSubmissions(subs) {
    // BLAZE IT: R y a n C e l s i u s ° S o u n d s
    const seen = new Set();
    return subs.filter(item => {
        if (seen.has(item.user.id)) {
            return false;
        } else {
            seen.add(item.user.id);
            return true;
        }
    });
}

function processSubmission(sub) {
    sub.formatted_created_at = utils.readableFormatDate(sub.created_at);
    sub.grade = utils.formatGrade(sub.grade);
    return sub;
}

function addSubmission(subs, newSub) {
    const idx = subs.findIndex(sub => sub.id === newSub.id);

    if (idx !== -1) {
        Vue.set(subs, idx, Object.assign({}, subs[idx], newSub));
        return subs;
    }

    const submissions = [...subs, newSub];
    submissions.sort((a, b) => -sortSubmissions(a, b, 'created_at'));
    return submissions;
}

const actions = {
    async loadSubmissionsByUser(context, { assignmentId, userId, force }) {
        await context.dispatch('loadSubmissions', assignmentId);

        if (force) {
            context.commit(types.SET_SUBMISSIONS_BY_USER_PROMISE, {
                assignmentId,
                userId,
                promise: null,
            });
        }

        if (context.state.submissionsByUserPromises[assignmentId][userId] == null) {
            const promise = axios
                .get(`/api/v1/assignments/${assignmentId}/users/${userId}/submissions/`)
                .then(({ data: subs }) => {
                    const submissions = subs.map(processSubmission);
                    submissions.forEach(sub => {
                        context.commit(types.ADD_SINGLE_SUBMISSION, { submission: sub });
                    });
                    return submissions;
                });
            context.commit(types.SET_SUBMISSIONS_BY_USER_PROMISE, {
                assignmentId,
                userId,
                promise,
            });
        }

        await context.state.submissionsByUserPromises[assignmentId][userId];

        return context.state.submissionsByUser[assignmentId][userId];
    },

    loadGivenSubmissions(context, { assignmentId, submissionIds }) {
        return Promise.all(
            submissionIds.map(submissionId =>
                context.dispatch('loadSingleSubmission', {
                    assignmentId,
                    submissionId,
                }),
            ),
        );
    },

    async loadSingleSubmission(context, { assignmentId, submissionId, force }) {
        // Don't wait for anything if we simply have the submission
        let submission = getSubmission(context.state, assignmentId, submissionId, false);
        if (submission != null && !force) {
            return submission;
        }

        await context.dispatch('loadSubmissions', assignmentId);

        if (context.state.singleSubmissionLoaders[submissionId] != null && !force) {
            return context.state.singleSubmissionLoaders[submissionId];
        }

        submission = getSubmission(context.state, assignmentId, submissionId, false);
        if (submission != null && !force) {
            return submission;
        }

        const promise = axios.get(`/api/v1/submissions/${submissionId}`).then(({ data }) => {
            const sub = processSubmission(data);
            context.commit(types.ADD_SINGLE_SUBMISSION, { submission: sub });
            return sub;
        });

        context.commit(types.SET_SINGLE_SUBMISSION_PROMISE, {
            submissionId,
            promise,
        });

        return promise.then(data => {
            context.commit(types.SET_SINGLE_SUBMISSION_PROMISE, {
                submissionId,
                promise: null,
            });
            return data;
        });
    },

    addSubmission({ commit }, { submission }) {
        submission.formatted_created_at = utils.readableFormatDate(submission.created_at);
        submission.grade = utils.formatGrade(submission.grade);
        return commit(types.ADD_SINGLE_SUBMISSION, { submission });
    },

    deleteSubmission({ dispatch }, { assignmentId }) {
        return dispatch('forceLoadSubmissions', assignmentId);
    },

    forceLoadSubmissions(context, assignmentId) {
        // This needs to be in one promise to make sure that two very quick
        // calls to `loadSubmissions` still only does one request (for the
        // same arguments of course).
        const promiseFun = async () => {
            await context.dispatch('courses/loadCourses', null, { root: true });

            await Promise.all([
                axios
                    .get(`/api/v1/assignments/${assignmentId}/submissions/?extended&latest_only`)
                    .then(({ data: submissions }) => submissions.map(processSubmission)),
                context.dispatch('courses/loadRubric', assignmentId, { root: true }),
                // TODO: Maybe not force load the graders here?
                context.dispatch('courses/forceLoadGraders', assignmentId, { root: true }),
            ]).then(([submissions]) => {
                context.commit(types.UPDATE_SUBMISSIONS, {
                    assignmentId,
                    submissions,
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
        const submission = getSubmission(state, assignmentId, submissionId, false);
        if (submission && submission.fileTree != null) {
            return null;
        }

        if (loaders.fileTrees[submissionId] == null) {
            const loader = Promise.all([
                dispatch('loadSingleSubmission', { assignmentId, submissionId }),
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
                ([, student, teacher]) => {
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
            loaders.fileTrees[submissionId] = loader;
        }

        return loaders.fileTrees[submissionId];
    },

    async loadSubmissionFeedback({ commit, dispatch, state }, { assignmentId, submissionId }) {
        const submission = getSubmission(state, assignmentId, submissionId, false);

        if (submission && submission.feedback != null) {
            return null;
        }

        if (loaders.feedback[submissionId] == null) {
            const loader = Promise.all([
                dispatch('loadSingleSubmission', { assignmentId, submissionId }),
                axios.get(`/api/v1/submissions/${submissionId}/feedbacks/`).catch(err => {
                    delete loaders.feedback[submissionId];
                    throw err;
                }),
            ]).then(([, { data }]) => {
                delete loaders.feedback[submissionId];
                if (data != null) {
                    commit(types.UPDATE_SUBMISSION, {
                        assignmentId,
                        submissionId,
                        submissionProps: {
                            feedback: new Feedback(data),
                        },
                    });
                }
            });

            loaders.feedback[submissionId] = loader;
        }

        return loaders.feedback[submissionId];
    },

    async addSubmissionFeedbackLine(
        { commit, state, dispatch },
        {
            assignmentId, submissionId, fileId, line, author,
        },
    ) {
        await dispatch('loadSingleSubmission', { assignmentId, submissionId });
        const submission = getSubmission(state, assignmentId, submissionId);

        commit(types.UPDATE_SUBMISSION_FEEDBACK, {
            submission,
            fileId,
            line,
            data: '',
            author,
        });
    },

    async submitSubmissionFeedbackLine(
        { commit, state, dispatch },
        {
            assignmentId, submissionId, fileId, line, data, author,
        },
    ) {
        await dispatch('loadSingleSubmission', { assignmentId, submissionId });
        const submission = getSubmission(state, assignmentId, submissionId);

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

    async deleteSubmissionFeedbackLine(
        { commit, state, dispatch },
        {
            assignmentId, submissionId, fileId, line, onServer,
        },
    ) {
        await dispatch('loadSingleSubmission', { assignmentId, submissionId });
        const submission = getSubmission(state, assignmentId, submissionId);

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

    async updateAutoTestTree(
        { commit, dispatch },
        {
            assignmentId, submissionId, autoTest, autoTestTree,
        },
    ) {
        await dispatch('loadSubmissionFileTree', { assignmentId, submissionId });

        const entries = [];
        autoTest.sets.forEach(set => {
            set.suites.forEach(suite => {
                if (autoTestTree[suite.id] == null) {
                    return;
                }

                entries.push({
                    id: null,
                    name: suite.rubricRow.header,
                    entries: autoTestTree[suite.id],
                });
            });
        });

        commit(types.UPDATE_SUBMISSION, {
            assignmentId,
            submissionId,
            submissionProps: {
                autoTestTree: {
                    id: null,
                    name: 'AutoTest generated files',
                    entries,
                },
            },
        });
    },
};

const mutations = {
    [types.UPDATE_SUBMISSIONS](state, { assignmentId, submissions }) {
        const newLatest = getLatestSubmissions(submissions);
        Vue.set(state.submissions, assignmentId, submissions);
        Vue.set(state.latestSubmissions, assignmentId, newLatest);
        Vue.set(state.groupSubmissionUsers, assignmentId, getUsersInGroup(newLatest));
        Vue.set(
            state.submissionsByUser,
            assignmentId,
            submissions.reduce((accum, val) => {
                accum[val.user.id] = [val];
                return accum;
            }, {}),
        );
        Vue.set(state.submissionsByUserPromises, assignmentId, {});
    },

    [types.SET_SUBMISSIONS_BY_USER_PROMISE](state, { assignmentId, userId, promise }) {
        const all = state.submissionsByUserPromises[assignmentId];
        Vue.set(all, userId, promise);
        Vue.set(state.submissionsByUserPromises, assignmentId, all);
    },

    [types.UPDATE_SUBMISSION_FEEDBACK](_, {
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

    [types.UPDATE_SUBMISSION](state, { assignmentId, submissionId, submissionProps }) {
        const submission = getSubmission(state, assignmentId, submissionId);

        Object.entries(submissionProps).forEach(([key, val]) => {
            if (key === 'id') {
                throw TypeError(`Cannot set submission property: ${key}`);
            } else if (key === 'autoTestTree') {
                Vue.set(submission.fileTree, 'autotest', val);
            } else if (key === 'grade') {
                Vue.set(submission, key, utils.formatGrade(val));
            } else {
                Vue.set(submission, key, val);
            }
        });
    },

    [types.SET_SUBMISSIONS_PROMISE](state, { promise, assignmentId }) {
        Vue.set(state.submissionsLoaders, assignmentId, promise);
    },

    [types.SET_SINGLE_SUBMISSION_PROMISE](state, { promise, submissionId }) {
        if (promise) {
            Vue.set(state.singleSubmissionLoaders, submissionId, promise);
        } else {
            Vue.delete(state.singleSubmissionLoaders, submissionId);
        }
    },

    [types.ADD_SINGLE_SUBMISSION](state, { submission }) {
        const userId = submission.user.id;
        const assignmentId = submission.assignment_id;
        const submissions = addSubmission(state.submissions[assignmentId] || [], submission);
        const userSubmissions = addSubmission(
            utils.getProps(state.submissionsByUser, [], assignmentId, userId),
            submission,
        );
        const oldLatest = state.latestSubmissions[assignmentId] || [];
        const newLatest = addToLatest(oldLatest, submission);

        Vue.set(state.submissions, assignmentId, submissions);
        Vue.set(state.latestSubmissions, assignmentId, newLatest);
        Vue.set(state.groupSubmissionUsers, assignmentId, getUsersInGroup(newLatest));
        if (state.submissionsByUser[assignmentId] == null) {
            Vue.set(state.submissionsByUser, assignmentId, { userId: userSubmissions });
        } else {
            Vue.set(state.submissionsByUser[assignmentId], userId, userSubmissions);
        }
    },

    [types.CLEAR_SUBMISSIONS](state) {
        Vue.set(state, 'submissions', {});
        Vue.set(state, 'latestSubmissions', {});
        Vue.set(state, 'submissionsByUser', {});
        Vue.set(state, 'submissionsByUserPromises', {});
        Vue.set(state, 'submissionsLoaders', {});
        Vue.set(state, 'singleSubmissionLoaders', {});
        Vue.set(state, 'groupSubmissionUsers', {});
        loaders.feedback = {};
        loaders.fileTrees = {};
    },
};

export default {
    namespaced: true,
    state: {
        submissions: {},
        latestSubmissions: {},
        submissionsByUser: {},
        submissionsByUserPromises: {},
        submissionsLoaders: {},
        singleSubmissionLoaders: {},
        groupSubmissionUsers: {},
    },

    getters,
    actions,
    mutations,
};
