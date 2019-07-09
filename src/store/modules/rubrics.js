import Vue from 'vue';
import axios from 'axios';

const getters = {
    rubrics: state => state.rubrics,
    results: state => state.results,
};

const loaders = {
    rubrics: {},
    results: {},
};

const actions = {
    loadRubric({ commit, state }, { assignmentId }) {
        if (state.rubrics[assignmentId]) {
            return Promise.resolve();
        }

        if (!loaders.rubrics[assignmentId]) {
            loaders.rubrics[assignmentId] = axios
                .get(`/api/v1/assignments/${assignmentId}/rubrics/`)
                .then(
                    ({ data: rubric }) => {
                        delete loaders.rubrics[assignmentId];
                        commit('updateRubric', { assignmentId, rubric });
                    },
                    err => {
                        delete loaders.rubrics[assignmentId];
                        throw err;
                    },
                );
        }

        return loaders.rubrics[assignmentId];
    },

    loadResult({ commit, state }, { submissionId, force }) {
        if (state.results[submissionId] && !force) {
            return Promise.resolve();
        }

        if (!loaders.results[submissionId]) {
            loaders.results[submissionId] = axios
                .get(`/api/v1/submissions/${submissionId}/rubrics/`)
                .then(
                    ({ data: result }) => {
                        delete loaders.results[submissionId];
                        commit('updateResult', { submissionId, result });
                    },
                    err => {
                        delete loaders.results[submissionId];
                        throw err;
                    },
                );
        }

        return loaders.results[submissionId];
    },

    clearResult({ commit, state }, { submissionId }) {
        if (state.results[submissionId]) {
            commit('clearResult', { submissionId });
        }
    },
};

const mutations = {
    updateRubric(state, { assignmentId, rubric }) {
        Vue.set(state.rubrics, assignmentId, rubric);
    },

    updateResult(state, { submissionId, result }) {
        Vue.set(state.results, submissionId, result);
    },

    clearResult(state, { submissionId }) {
        delete state.results[submissionId];
        Vue.set(state, 'results', state.results);
    },
};

export default {
    namespaced: true,
    state: {
        rubrics: {},
        results: {},
    },
    getters,
    actions,
    mutations,
};
