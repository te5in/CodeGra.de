/* SPDX-License-Identifier: AGPL-3.0-only */
import Vue from 'vue';
import axios from 'axios';

import * as utils from '@/utils';
import { Feedback } from '@/models/feedback';
import * as types from '../mutation-types';

const getters = {
    getFeedback: state => (assignmentId, submissionId) =>
        utils.getProps(state.feedbacks, null, assignmentId, submissionId),

    getReplyById: state => replyId => state.replies.get(replyId),
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
                axios
                    .get(`/api/v1/submissions/${submissionId}/feedbacks/?with_replies`)
                    .catch(err => {
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

    async addFeedbackLine({ commit, dispatch }, { assignmentId, submissionId, line }) {
        await dispatch('loadFeedback', { assignmentId, submissionId });

        commit(types.UPDATE_FEEDBACK, {
            assignmentId,
            submissionId,
            line,
        });
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

    [types.UPDATE_FEEDBACK](state, { assignmentId, submissionId, line }) {
        const feedback = utils.getProps(state.feedbacks, null, assignmentId, submissionId);
        let newFeedback;

        if (line.isEmpty) {
            newFeedback = feedback.removeFeedbackBase(line);
        } else {
            newFeedback = feedback.addFeedbackBase(line);
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
