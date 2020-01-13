/* SPDX-License-Identifier: AGPL-3.0-only */
import Vue from 'vue';
import axios from 'axios';

import * as utils from '@/utils';
import { Feedback, FeedbackLine } from '@/models/submission';
import * as types from '../mutation-types';

const getters = {
    getFeedback: state => (assignmentId, submissionId) =>
        utils.getProps(state.feedbacks, null, assignmentId, submissionId),
};

const loaders = {
    feedback: {},
};

const actions = {
    async loadFeedback(context, { assignmentId, submissionId, force }) {
        if (!force && context.getters.getFeedback(assignmentId, submissionId)) {
            return null;
        }

        if (force || loaders.feedback[submissionId] == null) {
            const loader = Promise.all([
                context.dispatch(
                    'submissions/loadSingleSubmission',
                    { assignmentId, submissionId },
                    {
                        root: true,
                    },
                ),
                axios.get(`/api/v1/submissions/${submissionId}/feedbacks/`).catch(err => {
                    delete loaders.feedback[submissionId];

                    switch (utils.getProps(err, null, 'response', 'status')) {
                        case 403:
                            return {};
                        default:
                            throw err;
                    }
                }),
            ]).then(([, { data }]) => {
                delete loaders.feedback[submissionId];
                if (data != null) {
                    context.commit(types.SET_FEEDBACK, {
                        assignmentId,
                        submissionId,
                        feedback: Feedback.fromServerData(data),
                    });
                }
            });

            loaders.feedback[submissionId] = loader;
        }

        return loaders.feedback[submissionId];
    },

    async addFeedbackLine(
        { commit, dispatch },
        {
            assignmentId, submissionId, fileId, line, author,
        },
    ) {
        await dispatch('loadFeedback', { assignmentId, submissionId });

        commit(types.UPDATE_FEEDBACK, {
            assignmentId,
            submissionId,
            fileId,
            line,
            data: '',
            author,
        });
    },

    async submitFeedbackLine(
        { commit, dispatch },
        {
            assignmentId, submissionId, fileId, line, data, author,
        },
    ) {
        return Promise.all([
            dispatch('loadFeedback', { assignmentId, submissionId }),
            axios.put(`/api/v1/code/${fileId}/comments/${line}`, { comment: data }),
        ]).then(([, response]) => {
            response.onAfterSuccess = () =>
                commit(types.UPDATE_FEEDBACK, {
                    assignmentId,
                    submissionId,
                    fileId,
                    line,
                    data,
                    author,
                });
            return response;
        });
    },

    async deleteFeedbackLine(
        { commit, dispatch },
        {
            assignmentId, submissionId, fileId, line, onServer,
        },
    ) {
        await dispatch('loadFeedback', { assignmentId, submissionId });

        function cont() {
            commit(types.UPDATE_FEEDBACK, {
                assignmentId,
                submissionId,
                fileId,
                line,
                data: null,
            });
        }

        if (onServer) {
            return axios.delete(`/api/v1/code/${fileId}/comments/${line}`).then(response => {
                response.onAfterSuccess = cont;
                return response;
            });
        } else {
            return Promise.resolve({ onSuccess: cont });
        }
    },

    deleteFeedback({ commit }, { assignmentId }) {
        commit(types.DELETE_FEEDBACK, { assignmentId });
    },
};

const mutations = {
    [types.SET_FEEDBACK](state, { assignmentId, submissionId, feedback }) {
        const trees = utils.getProps(state.feedbacks, {}, assignmentId);
        Vue.set(trees, submissionId, feedback);
        Vue.set(state.feedbacks, assignmentId, trees);
    },

    [types.DELETE_FEEDBACK](state, { assignmentId }) {
        Vue.delete(state.feedbacks, assignmentId);
    },

    [types.DELETE_ALL_FEEDBACKS](state) {
        Vue.set(state, 'feedbacks', {});
        loaders.feedbacks = {};
    },

    [types.UPDATE_FEEDBACK](state, {
        assignmentId, submissionId, fileId, line, data, author,
    }) {
        const feedback = utils.getProps(state.feedbacks, null, assignmentId, submissionId);
        let newFeedback;

        if (data == null) {
            newFeedback = feedback.removeFeedbackLine(fileId, line);
        } else {
            const newLine = new FeedbackLine(fileId, line, data, author);
            newFeedback = feedback.addFeedbackLine(newLine);
        }

        Vue.set(state.feedbacks[assignmentId], submissionId, newFeedback);
    },
};

export default {
    namespaced: true,
    state: {
        feedbacks: {},
    },

    getters,
    actions,
    mutations,
};
