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
import analytics from './modules/analytics';
import plagiarism from './modules/plagiarism';
import submissions from './modules/submissions';
import code from './modules/code';
import users from './modules/users';
import fileTrees from './modules/file_trees';
import feedback from './modules/feedback';

Vue.use(Vuex);

const debug = process.env.NODE_ENV !== 'production';
const plugins = [];

let disabledPersistance = false;
let toastMessage = null;

try {
    plugins.push(
        createPersistedState({
            paths: ['user', 'pref'],
            storage: {
                getItem: key => window.localStorage.getItem(key),
                setItem: (key, value) => {
                    if (disabledPersistance && key !== '@@') {
                        const cleanedValue = {
                            pref: JSON.parse(value).pref,
                        };
                        return window.localStorage.setItem(key, JSON.stringify(cleanedValue));
                    }
                    return window.localStorage.setItem(key, value);
                },
                removeItem: key => window.localStorage.removeItem(key),
            },
        }),
    );
} catch (e) {
    Vue.use(Toasted);
    toastMessage = Vue.toasted.error(
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

export const store = new Vuex.Store({
    modules: {
        user,
        pref,
        courses,
        rubrics,
        autotest,
        analytics,
        plagiarism,
        submissions,
        code,
        users,
        fileTrees,
        feedback,
    },
    strict: debug,
    plugins,
});

export function disablePersistance() {
    disabledPersistance = true;
    if (toastMessage != null) {
        toastMessage.goAway(0);
    }
}
