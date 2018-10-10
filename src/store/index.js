/* SPDX-License-Identifier: AGPL-3.0-only */
import Vue from 'vue';
import Vuex from 'vuex';
import createPersistedState from 'vuex-persistedstate';

import user from './modules/user';
import pref from './modules/preference';
import courses from './modules/courses';
import plagiarism from './modules/plagiarism';

Vue.use(Vuex);

const debug = process.env.NODE_ENV !== 'production';
const plugins = [];

try {
    plugins.push(createPersistedState({
        paths: ['user', 'pref'],
    }));
} catch (e) {
    // NOOP
}

export default new Vuex.Store({
    modules: {
        user,
        pref,
        courses,
        plagiarism,
    },
    strict: debug,
    plugins,
});
