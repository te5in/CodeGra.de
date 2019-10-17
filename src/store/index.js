/* SPDX-License-Identifier: AGPL-3.0-only */
import Vue from 'vue';
import Vuex from 'vuex';
import createPersistedState from 'vuex-persistedstate';
import Toasted from 'vue-toasted';

import user from './modules/user';
import pref from './modules/preference';
import courses from './modules/courses';
import rubrics from './modules/rubrics';
import autotest from './modules/autotest';
import plagiarism from './modules/plagiarism';
import submissions from './modules/submissions';
import code from './modules/code';

Vue.use(Vuex);

const debug = process.env.NODE_ENV !== 'production';
const plugins = [];

try {
    plugins.push(
        createPersistedState({
            paths: ['user', 'pref'],
        }),
    );
} catch (e) {
    Vue.use(Toasted);
    Vue.toasted.error(
        'Unable to persistently store user credentials, please check you browser privacy levels. You will not be logged-in in other tabs or when reloading.',
        {
            position: 'bottom-center',
            fullWidth: true,
            closeOnSwipe: false,
            fitToScreen: true,
            action: {
                text: '✖',
                onClick(_, toastObject) {
                    toastObject.goAway(0);
                },
            },
        },
    );
}

export default new Vuex.Store({
    modules: {
        user,
        pref,
        courses,
        rubrics,
        autotest,
        plagiarism,
        submissions,
        code,
    },
    strict: debug,
    plugins,
});
