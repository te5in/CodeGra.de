// SPDX-License-Identifier: AGPL-3.0-only
import snappyJs from 'snappyjs';
import Vue from 'vue';
import axios from 'axios';
import Deque from '@/utils/deque';
import * as types from '../mutation-types';

const MAX_CACHE_SIZE = 10 * 2 ** 20;

const getters = {
    getCachedCode: state => route => {
        const cached = state.cacheMap[route];
        if (cached == null) {
            return null;
        }
        return snappyJs.uncompress(cached);
    },
};

const loaders = {
    codeLoaders: {},
};

const actions = {
    accessedCode({ commit }, route) {
        commit(types.UPDATE_LATEST_ACCESS, route);
    },

    loadCode(context, codeId) {
        return context.dispatch('loadCodeFromRoute', {
            route: `/api/v1/code/${codeId}`,
        });
    },

    loadCodeFromRoute(context, { route }) {
        const cached = context.getters.getCachedCode(route);
        if (cached != null) {
            context.dispatch('accessedCode', route);
            return cached;
        }

        if (route in loaders.codeLoaders) {
            return loaders.codeLoaders[route];
        }

        let promise;

        const clearLoader = () => {
            promise = undefined;
            Vue.delete(loaders.codeLoaders, route);
        };

        promise = axios
            .get(route, {
                responseType: 'arraybuffer',
            })
            .then(
                code => {
                    context.commit(types.SET_CODE_CACHE, {
                        route,
                        code: code.data,
                    });
                    clearLoader();
                    return code.data;
                },
                err => {
                    clearLoader();
                    throw err;
                },
            );

        Vue.set(loaders.codeLoaders, route, promise);
        return promise;
    },
};

function getClearState() {
    return {
        cacheMap: {},
        cacheDeque: new Deque(),
        cacheSize: 0,
    };
}

const mutations = {
    [types.CLEAR_CODE_CACHE](state) {
        Object.entries(getClearState()).forEach(([key, value]) => {
            Vue.set(state, key, value);
        });
    },

    [types.UPDATE_LATEST_ACCESS](state, route) {
        const deq = state.cacheDeque;

        if (deq.isEmpty()) {
            return;
        }

        const lastVal = deq.peekFront();
        if (lastVal === route) {
            return;
        }

        for (let len = state.cacheDeque.length, oldVal = lastVal, i = 1; i < len; ++i) {
            const prevVal = deq.setAt(i, oldVal);

            if (prevVal === route) {
                // We just overridden the value we want at the beginning, so we
                // set it at index 0 and we are done.
                deq.setAt(0, prevVal);
                break;
            } else {
                oldVal = prevVal;
            }
        }

        Vue.set(state, 'cacheDeque', deq);
    },

    [types.SET_CODE_CACHE](state, { route, code }) {
        const deq = state.cacheDeque;
        const cacheMap = state.cacheMap;
        const compressed = snappyJs.compress(code);
        if (compressed.byteLength > MAX_CACHE_SIZE) {
            return;
        }

        let cacheSize = state.cacheSize + compressed.byteLength;
        const removedIds = [];

        while (cacheSize > MAX_CACHE_SIZE && !deq.isEmpty()) {
            const toDeleteId = deq.pop();
            const toDelete = cacheMap[toDeleteId];

            if (toDelete != null) {
                cacheSize -= toDelete.byteLength;
                removedIds.push(toDeleteId);
            }
        }

        for (let i = removedIds.length - 1; i >= 0; --i) {
            const removedId = removedIds[i];
            const item = cacheMap[removedId];

            if (cacheSize + item.byteLength < MAX_CACHE_SIZE) {
                deq.push(removedId);
                cacheSize += item.byteLength;
            } else {
                Vue.delete(state.cacheMap, removedId);
            }
        }

        deq.unshift(route);
        Vue.set(state.cacheMap, route, compressed);

        state.cacheSize = cacheSize;
        state.cacheDeque = deq;
    },
};

export default {
    namespaced: true,
    state: getClearState(),

    getters,
    actions,
    mutations,
};
