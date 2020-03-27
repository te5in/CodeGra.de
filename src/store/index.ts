/* SPDX-License-Identifier: AGPL-3.0-only */
import Vue from 'vue';
import Vuex from 'vuex';
// @ts-ignore
import createPersistedState from 'vuex-persistedstate';
// @ts-ignore
import Toasted from 'vue-toasted';

import { getStoreBuilder } from 'vuex-typex';

import user from './modules/user';
import pref from './modules/preference';
import courses from './modules/courses';
import rubrics from './modules/rubrics';
import autotest from './modules/autotest';
import plagiarism from './modules/plagiarism';
import submissions from './modules/submissions';
import code from './modules/code';
import users from './modules/users';
import fileTrees from './modules/file_trees';
import feedback from './modules/feedback';

// We import this for the side effect only.
import './modules/notification';

import { RootState } from './state';

Vue.use(Vuex);

const debug = process.env.NODE_ENV !== 'production';
const plugins = [];

let disabledPersistance = false;
let toastMessage: any = null;

try {
    plugins.push(
        createPersistedState({
            paths: ['user', 'pref'],
            storage: {
                getItem: (key: string) => window.localStorage.getItem(key),
                setItem: (key: string, value: string) => {
                    if (disabledPersistance && key !== '@@') {
                        const cleanedValue = {
                            pref: JSON.parse(value).pref,
                        };
                        return window.localStorage.setItem(key, JSON.stringify(cleanedValue));
                    }
                    return window.localStorage.setItem(key, value);
                },
                removeItem: (key: string) => window.localStorage.removeItem(key),
            },
        }),
    );
} catch (e) {
    Vue.use(Toasted);
    toastMessage = (Vue as any).toasted.error(
        'Unable to persistently store user credentials, please check you browser privacy levels. You will not be logged-in in other tabs or when reloading.',
        {
            position: 'bottom-center',
            fullWidth: true,
            closeOnSwipe: false,
            fitToScreen: true,
            action: {
                text: '✖',
                onClick(_: Object, toastObject: any) {
                    toastObject.goAway(0);
                },
            },
        },
    );
}

const rootBuilder = getStoreBuilder<RootState>();

Object.entries({
    user,
    pref,
    courses,
    rubrics,
    autotest,
    plagiarism,
    submissions,
    code,
    users,
    fileTrees,
    feedback,
}).forEach(([key, value]) => {
    const builder = rootBuilder.module(key);
    builder.vuexModule = () => value;
});

export const store = rootBuilder.vuexStore({
    strict: debug,
    plugins,
});

export function disablePersistance() {
    disabledPersistance = true;
    if (toastMessage != null) {
        toastMessage.goAway(0);
    }
}
