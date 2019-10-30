import Vue from 'vue';
import axios from 'axios';

import { RubricResult } from '@/models/rubric';
import * as types from '../mutation-types';

const getters = {
    results: state => state.results,
};

const loaders = {
    results: {},
};

const actions = {
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
            .then(() => commit('setSelected', { result, selected, submissionId }));
    },

    toggleRubricItem({ commit, state }, { submissionId, row, item }) {
        if (row.locked) {
            throw new Error('Rubric row is locked');
        }

        const result = state.results[submissionId];
        const isSelected = result.selected.find(x => x.id === item.id);
        const commitProps = {
            result,
            row,
            item,
            submissionId,
        };

        if (!UserConfig.features.incremental_rubric_submission) {
            commit(isSelected ? 'unselectItem' : 'selectItem', commitProps);
            return Promise.resolve();
        } else if (isSelected) {
            return axios
                .patch(`/api/v1/submissions/${submissionId}/rubricitems/${item.id}`)
                .then(() => commit('selectItem', commitProps));
        } else {
            return axios
                .delete(`/api/v1/submissions/${submissionId}/rubricitems/${item.id}`)
                .then(() => commit('unselectItem', commitProps));
        }
    },
};

export const mutations = {
    setResult(state, { submissionId, result }) {
        Vue.set(state.results, submissionId, new RubricResult(result));
    },

    clearResult(state, { submissionId }) {
        delete state.results[submissionId];
        Vue.set(state, 'results', state.results);
    },

    [types.CLEAR_RUBRIC_RESULTS](state) {
        Vue.set(state, 'results', {});
    },

    setSelected(state, { result, selected, submissionId }) {
        Vue.set(state.results, submissionId, result.setSelected(selected));
    },

    selectItem(state, {
        result, row, item, submissionId,
    }) {
        Vue.set(state.results, submissionId, result.selectItem(row, item));
    },

    unselectItem(state, {
        result, row, item, submissionId,
    }) {
        Vue.set(state.results, submissionId, result.unselectItem(row, item));
    },
};

export default {
    namespaced: true,
    state: {
        results: {},
    },
    getters,
    actions,
    mutations,
};
