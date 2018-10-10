/* SPDX-License-Identifier: AGPL-3.0-only */
import axios from 'axios';
import Vue from 'vue';

import * as types from '../mutation-types';

const getters = {
    runs: state => state.runs,
};

const actions = {
    loadRun({ state, commit }, runId) {
        if (state.curPromises[runId] == null) {
            state.curPromises[runId] = Promise.all([
                axios.get(`/api/v1/plagiarism/${runId}/cases/`),
                axios.get(`/api/v1/plagiarism/${runId}?extended`),
            ]).then(async ([{ data: serverCases }, { data: run }]) => {
                run.cases = (serverCases || []).map((serverCase) => {
                    if (serverCase.assignments[0].id !== run.assignment.id) {
                        serverCase.assignments.reverse();
                        serverCase.users.reverse();
                        serverCase.submissions.reverse();
                    }
                    serverCase.canView = (serverCase.submissions != null &&
                                          serverCase.assignments[0].id != null &&
                                          serverCase.assignments[1].id != null);
                    if (serverCase.canView) {
                        // eslint-disable-next-line
                        serverCase._rowVariant = 'info';
                    } else {
                        // eslint-disable-next-line
                        serverCase._rowVariant = 'warning';
                    }
                    return serverCase;
                });
                await commit(types.SET_PLAGIARISM_RUN, run);
                return run;
            });
        }
        return state.curPromises[runId];
    },

    async refreshRun({ dispatch }, runId) {
        await dispatch('removeRun', runId);
        return dispatch('loadRun', runId);
    },

    removeRun({ commit }, runId) {
        commit(types.CLEAR_PLAGIARISM_RUN, runId);
    },

    clear({ commit }) {
        commit(types.CLEAR_PLAGIARISM_RUNS);
    },
};

const mutations = {
    [types.SET_PLAGIARISM_RUN](state, run) {
        Vue.set(state.runs, run.id, run || {});
    },

    [types.CLEAR_PLAGIARISM_RUN](state, runId) {
        Vue.set(state.runs, runId, undefined);
        Vue.set(state.curPromises, runId, undefined);

        delete state.runs[runId];
        delete state.curPromises[runId];
    },

    [types.CLEAR_PLAGIARISM_RUNS](state) {
        state.runs = {};
        state.curPromises = {};
    },
};

export default {
    namespaced: true,
    state: {
        runs: {},
        curPromises: {},
    },
    getters,
    actions,
    mutations,
};
