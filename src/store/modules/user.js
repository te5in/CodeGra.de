/* SPDX-License-Identifier: AGPL-3.0-only */
import Vue from 'vue';
import axios from 'axios';
import { parseWarningHeader } from '@/utils';
import * as types from '../mutation-types';

const UNLOADED_SNIPPETS = {};
let snippetsLastReloaded;

const getters = {
    loggedIn: state => state.id !== 0,
    id: state => state.id,
    snippets: state => state.snippets,
    name: state => state.name,
    username: state => state.username,
    canSeeHidden: state => state.canSeeHidden,
    findSnippetsByPrefix(state) {
        let values = [];
        if (state && state.snippets !== UNLOADED_SNIPPETS) {
            values = Object.values(
                state.snippets,
            ).sort((a, b) => a.key.localeCompare(b.key));
        }

        return prefix => values.filter(
            ({ key }) => key.startsWith(prefix),
        );
    },
};

const actions = {
    login({ commit, state }, { username, password, onWarning }) {
        state.jwtToken = null;
        return new Promise((resolve, reject) => {
            axios.post('/api/v1/login', { username, password }).then(async (response) => {
                // Allow the warning to be shown somewhere before actually
                // logging in.
                if (onWarning != null && response.headers.warning) {
                    await onWarning(
                        parseWarningHeader(response.headers.warning),
                        response,
                    );
                }
                commit(types.LOGIN, response.data);
                resolve(response);
                actions.refreshSnippets({ commit });
            }).catch((err) => {
                if (err.response) {
                    reject(err.response.data);
                } else {
                    reject(new Error('Login failed for a unknown reason!'));
                }
            });
        });
    },

    addSnippet({ commit }, snippet) {
        commit(types.NEW_SNIPPET, snippet);
    },

    updateSnippet({ commit }, snippet) {
        commit(types.UPDATE_SNIPPET, snippet);
    },

    deleteSnippet({ commit }, snippet) {
        commit(types.REMOVE_SNIPPET, snippet);
    },

    refreshSnippets({ commit }) {
        return new Promise((resolve) => {
            axios.get('/api/v1/snippets/').then(({ data }) => {
                const snips = {};
                for (let i = 0, len = data.length; i < len; i += 1) {
                    snips[data[i].key] = data[i];
                }
                commit(types.SNIPPETS, snips);
                snippetsLastReloaded = Date.now();
                resolve();
            });
        });
    },

    maybeRefreshSnippets({ commit, state }) {
        if (!state || state.snippets === UNLOADED_SNIPPETS) {
            return actions.refreshSnippets({ commit });
        }

        const diff = (Date.now() - snippetsLastReloaded) / (60 * 1000);

        if (diff > 5 && Math.random() < ((diff - 5) / (60 * 24)) ** 2) {
            return actions.refreshSnippets({ commit });
        }

        return null;
    },

    logout({ commit }) {
        return Promise.all([
            commit(`courses/${types.CLEAR_COURSES}`, null, { root: true }),
            commit(`plagiarism/${types.CLEAR_PLAGIARISM_RUNS}`, null, { root: true }),
            commit(types.LOGOUT),
        ]);
    },

    verifyLogin({ commit, state, dispatch }) {
        return new Promise((resolve, reject) => {
            axios.get('/api/v1/login?type=extended').then((response) => {
                // We are already logged in. Update state to logged in state
                commit(types.LOGIN, {
                    access_token: state.jwtToken,
                    user: response.data,
                });
                resolve();
            }).catch(() => {
                dispatch('logout').then(reject, reject);
            });
        });
    },

    updateUserInfo({ commit }, {
        name, email, oldPw, newPw,
    }) {
        return axios.patch('/api/v1/login', {
            name,
            email,
            old_password: oldPw,
            new_password: newPw,
        }).then(() => {
            commit(types.UPDATE_USER_INFO, { name, email });
        });
    },

    updateAccessToken({ dispatch, commit }, newToken) {
        return dispatch('logout').then(() => {
            commit(types.SET_ACCESS_TOKEN, newToken);
        });
    },
};

const mutations = {
    [types.LOGIN](state, data) {
        state.jwtToken = data.access_token;

        const userdata = data.user;
        state.id = userdata.id;
        state.email = userdata.email;
        state.name = userdata.name;
        state.canSeeHidden = userdata.hidden;
        state.username = userdata.username;
    },

    [types.SNIPPETS](state, snippets) {
        state.snippets = snippets;
    },

    [types.LOGOUT](state) {
        state.id = 0;
        state.name = '';
        state.email = '';
        state.snippets = UNLOADED_SNIPPETS;
        state.canSeeHidden = false;
        state.jwtToken = null;
        state.username = null;
        Vue.prototype.$clearPermissions();
    },

    [types.NEW_SNIPPET](state, { id, key, value }) {
        Vue.prototype.$set(state.snippets, key, { id, key, value });
    },

    [types.UPDATE_SNIPPET](state, { id, key, value }) {
        const oldKey = Object.entries(state.snippets).find(
            ([, snippet]) => snippet.id === id,
        )[0];
        delete state.snippets[oldKey];
        Vue.prototype.$set(state.snippets, key, { id, key, value });
    },

    [types.REMOVE_SNIPPET](state, { key }) {
        const newSnippets = Object.assign({}, state.snippets);
        delete newSnippets[key];
        state.snippets = newSnippets;
    },

    [types.UPDATE_USER_INFO](state, { name, email }) {
        state.name = name;
        state.email = email;
    },

    [types.SET_ACCESS_TOKEN](state, accessToken) {
        state.jwtToken = accessToken;
    },

    [types.CLEAR_CACHE](state) {
        state.snippets = UNLOADED_SNIPPETS;
    },
};

export default {
    namespaced: true,
    state: {
        jwtToken: null,
        id: 0,
        email: '',
        name: '',
        snippets: UNLOADED_SNIPPETS,
        canSeeHidden: false,
        username: '',
    },
    getters,
    actions,
    mutations,
};
