/* SPDX-License-Identifier: AGPL-3.0-only */
import * as types from '../mutation-types';

const getters = {
    fontSize: state => state.fontSize,
    darkMode: state => state.darkMode,
    contextAmount: state => state.contextAmount,
};

const actions = {
    setFontSize({ commit }, val) {
        commit(types.UPDATE_PREF, { key: 'fontSize', val });
    },
    setContextAmount({ commit }, val) {
        commit(types.UPDATE_PREF, { key: 'contextAmount', val });
    },
    setDarkMode({ commit }, val) {
        commit(types.UPDATE_PREF, { key: 'darkMode', val });
    },
};

const mutations = {
    [types.UPDATE_PREF](state, { key, val }) {
        if (!Object.hasOwnProperty.call(state, key)) {
            throw new ReferenceError(`Invalid preference key: ${key}`);
        }
        state[key] = val;
    },
};

export default {
    namespaced: true,
    state: {
        fontSize: 12,
        darkMode: false,
        contextAmount: 3,
    },
    getters,
    actions,
    mutations,
};
