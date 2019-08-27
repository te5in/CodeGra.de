import Vue from 'vue';
import axios from 'axios';

import { Rubric, RubricResult } from '@/models/rubric';
import { getProps } from '@/utils';

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
        if (assignmentId in state.rubrics) {
            return Promise.resolve();
        }

        if (!loaders.rubrics[assignmentId]) {
            loaders.rubrics[assignmentId] = axios
                .get(`/api/v1/assignments/${assignmentId}/rubrics/`)
                .then(
                    ({ data: rubric }) => {
                        delete loaders.rubrics[assignmentId];
                        commit('setRubric', { assignmentId, rubric });
                    },
                    err => {
                        delete loaders.rubrics[assignmentId];
                        switch (getProps(err, null, 'response', 'status')) {
                            case 404:
                                commit('setRubric', { assignmentId, rubric: null });
                                break;
                            default:
                                throw err;
                        }
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
                        commit('setResult', { submissionId, result });
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

    updateRubricItems({ commit, state }, { submissionId, selected }) {
        const result = state.results[submissionId];

        return axios
            .patch(`/api/v1/submissions/${submissionId}/rubricitems/`, {
                items: selected.map(x => x.id),
            })
            .then(() => commit('setSelected', { result, selected }));
    },

    toggleRubricItem({ commit, state }, { submissionId, row, item }) {
        if (row.locked) {
            throw new Error('Rubric row is locked');
        }

        const result = state.results[submissionId];
        const isSelected = result.selected.find(x => x.id === item.id);

        if (!UserConfig.features.incremental_rubric_submission) {
            commit(isSelected ? 'unselectItem' : 'selectItem', { result, row, item });
            return Promise.resolve();
        } else if (isSelected) {
            return axios
                .patch(`/api/v1/submissions/${submissionId}/rubricitems/${item.id}`)
                .then(() => commit('selectItem', { result, row, item }));
        } else {
            return axios
                .delete(`/api/v1/submissions/${submissionId}/rubricitems/${item.id}`)
                .then(() => commit('unselectItem', { result, row, item }));
        }
    },
};

export const mutations = {
    setRubric(state, { assignmentId, rubric }) {
        const newRubric = rubric ? new Rubric(rubric) : null;
        Vue.set(state.rubrics, assignmentId, newRubric);
    },

    clearRubric(state, { assignmentId }) {
        Vue.delete(state.rubrics, assignmentId);
    },

    setResult(state, { submissionId, result }) {
        Vue.set(state.results, submissionId, new RubricResult(result));
    },

    clearResult(state, { submissionId }) {
        delete state.results[submissionId];
        Vue.set(state, 'results', state.results);
    },

    setSelected(state, { result, selected }) {
        result.setSelected(selected);
    },

    selectItem(state, { result, row, item }) {
        result.selectItem(row, item);
    },

    unselectItem(state, { result, row, item }) {
        result.unselectItem(row, item);
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
