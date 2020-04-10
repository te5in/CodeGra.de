/* SPDX-License-Identifier: AGPL-3.0-only */
import 'bootstrap/dist/css/bootstrap.css';
import 'bootstrap-vue/dist/bootstrap-vue.css';
import 'highlightjs/styles/solarized-dark.css';
import 'vue-multiselect/dist/vue-multiselect.min.css';
import '@/style.less';

import Icon from 'vue-awesome/components/Icon';
import Vue from 'vue';
import BootstrapVue from 'bootstrap-vue';
import axios from 'axios';
import axiosRetry from 'axios-retry';
import Toasted from 'vue-toasted';
import localforage from 'localforage';
import memoryStorageDriver from 'localforage-memoryStorageDriver';
import VueMasonry from 'vue-masonry-css';
import VueClipboard from 'vue-clipboard2';
import moment from 'moment';

import '@/polyfills';
import App from '@/App';
import router, { setRestoreRoute } from '@/router';
import * as utils from '@/utils';
import { store } from './store';
import * as mutationTypes from './store/mutation-types';

Vue.use(BootstrapVue);
Vue.use(Toasted);
Vue.use(VueMasonry);
Vue.use(VueClipboard);

Vue.config.productionTip = false;

moment.relativeTimeThreshold('h', 48);

Icon.register({
    tilde: {
        width: 24,
        height: 24,
        d:
            'M2,15C2,15 2,9 8,9C12,9 12.5,12.5 15.5,12.5C19.5,12.5 19.5,9 19.5,9H22C22,9 22,15 16,15C12,15 10.5,11.5 8.5,11.5C4.5,11.5 4.5,15 4.5,15H2',
    },
    diff: {
        width: 896,
        height: 1024,
        d:
            'M448 256H320v128H192v128h128v128h128V512h128V384H448V256zM192 896h384V768H192V896zM640 0H128v64h480l224 224v608h64V256L640 0zM0 128v896h768V320L576 128H0zM704 960H64V192h480l160 160V960z',
    },
    progress: {
        width: 1894,
        height: 1894,
        d:
            'm 448,1088 c -53.3333,0 -98.6667,-18.6667 -136,-56 -37.3333,-37.3333 -56,-82.6667 -56,-136 0,-53.3333 18.6667,-98.6667 56,-136 37.3333,-37.3333 82.6667,-56 136,-56 40,0 76.6667,11.6667 110,35 33.3333,23.3333 57,54.3333 71,93 h 651 V 960 H 629 c -14,38.6667 -37.6667,69.6667 -71,93 -33.3333,23.3333 -70,35 -110,35 z m 0,128 c 51.3333,0 99.3333,-11.3333 144,-34 44.6667,-22.6667 82,-54 112,-94 h 768 c 53.3333,0 98.6667,-18.6667 136,-56 37.3333,-37.3333 56,-82.6667 56,-136 0,-53.3333 -18.6667,-98.6667 -56,-136 -37.3333,-37.3333 -82.6667,-56 -136,-56 H 704 C 674,664 636.6667,632.6667 592,610 547.3333,587.3333 499.3333,576 448,576 359.3333,576 283.8333,607.1667 221.5,669.5 159.1667,731.8333 128,807.3333 128,896 c 0,88.6667 31.1667,164.1667 93.5,226.5 62.3333,62.3333 137.8333,93.5 226.5,93.5 z m 0,128 C 324.6667,1344 219.1667,1300.1667 131.5,1212.5 43.8333,1124.8333 0,1019.3333 0,896 0,772.6667 43.8333,667.1667 131.5,579.5 219.1667,491.83333 324.6667,448 448,448 c 121.3333,0 225.6667,42.66667 313,128 h 711 c 88.6667,0 164.1667,31.1667 226.5,93.5 62.3333,62.3333 93.5,137.8333 93.5,226.5 0,88.6667 -31.1667,164.1667 -93.5,226.5 -62.3333,62.3333 -137.8333,93.5 -226.5,93.5 H 761 c -87.3333,85.3333 -191.6667,128 -313,128 z',
    },
});

axios.defaults.transformRequest.push((data, headers) => {
    if (store.state.user.jwtToken) {
        headers.Authorization = `Bearer ${store.state.user.jwtToken}`;
    }
    return data;
});

// Fix axios automatically parsing all responses as JSON... WTF!!!
axios.defaults.transformResponse = [
    function defaultTransformResponse(data, headers) {
        switch (headers['content-type']) {
            case 'application/json':
                // Somehow axios gives us an ArrayBuffer sometimes, even though
                // the Content-Type header is application/json. JSON.parse does
                // not work on ArrayBuffers (they're silently converted to the
                // string "[object ArrayBuffer]", which is invalid JSON), so we
                // must do that ourselves.
                if (data instanceof ArrayBuffer) {
                    const view = new Int8Array(data);
                    const dataStr = String.fromCharCode.apply(null, view);
                    return JSON.parse(dataStr);
                }
                return JSON.parse(data);
            default:
                return data;
        }
    },
];

axiosRetry(axios, {
    retries: 3,
    retryDelay: (retryNumber = 0) => {
        const delay = 2 ** retryNumber * 500;
        const randomSum = delay * 0.2 * Math.random(); // 0-20% of the delay
        return delay + randomSum;
    },
});

axios.interceptors.response.use(
    response => response,
    (() => {
        let toastVisible = false;
        return error => {
            const { config, response, request } = error;

            if (!toastVisible && !response && request) {
                toastVisible = true;
                Vue.toasted.error(
                    'There was an error connecting to the server... Please try again later',
                    {
                        position: 'bottom-center',
                        closeOnSwipe: false,
                        duration: 3000,
                        onComplete: () => {
                            toastVisible = false;
                        },
                    },
                );
            } else if (
                config &&
                config.method === 'get' &&
                response.status === 401 &&
                !config.url.match(/\/api\/v1\/login.*/)
            ) {
                if (router.currentRoute.name !== 'login') {
                    setRestoreRoute(router.currentRoute);
                    store.dispatch('user/logout').then(() => {
                        router.push({ name: 'login' });
                    });
                }
                if (!toastVisible) {
                    toastVisible = true;
                    Vue.toasted.error(
                        'You are currently not logged in. Please log in to view this page.',
                        {
                            position: 'bottom-center',
                            closeOnSwipe: false,
                            action: {
                                text: '✖',
                                onClick(_, toastObject) {
                                    toastObject.goAway(0);
                                    toastVisible = false;
                                },
                            },
                        },
                    );
                }
            }

            throw error;
        };
    })(),
);

Vue.prototype.$http = axios;

const DRIVERS = [
    localforage.INDEXEDDB,
    localforage.WEBSQL,
    localforage.LOCALSTORAGE,
    'memoryStorageDriver',
];

let inLTI = false;
Vue.util.defineReactive(
    Vue.prototype,
    '$inLTI',
    inLTI,
    val => {
        if (val === true) {
            inLTI = val;
        } else {
            throw new TypeError('You can only set $inLTI to true');
        }
    },
    true,
);

let ltiProvider = null;
Vue.util.defineReactive(
    Vue.prototype,
    '$ltiProvider',
    ltiProvider,
    val => {
        if (ltiProvider === null) {
            ltiProvider = val;
        } else {
            throw new TypeError('You can only set $ltiProvider once');
        }
    },
    true,
);

let LTIAssignmentId = null;
Vue.util.defineReactive(
    Vue.prototype,
    '$LTIAssignmentId',
    LTIAssignmentId,
    val => {
        if (val == null) {
            throw new TypeError('You cannot set this to null or undefined');
        }
        if (LTIAssignmentId == null || val === LTIAssignmentId) {
            LTIAssignmentId = val;
        } else {
            throw new TypeError('You cannot change this property once it is set');
        }
    },
    true,
);

try {
    Vue.prototype.$devMode = process.env.NODE_ENV === 'development';
} catch (e) {
    Vue.prototype.$devMode = false;
}
Vue.prototype.$utils = utils;
Vue.prototype.$userConfig = UserConfig;

Vue.prototype.$afterRerender = function doubleRequestAnimationFrame(cb) {
    return new Promise(resolve => {
        this.$nextTick(() => {
            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    if (cb) {
                        cb();
                    }
                    resolve();
                });
            });
        });
    });
};

// eslint-disable-next-line
localforage.defineDriver(memoryStorageDriver).then(() => {
    Vue.prototype.$hlanguageStore = localforage.createInstance({
        name: 'highlightLanguageStore',
        driver: DRIVERS,
    });
    Vue.prototype.$whitespaceStore = localforage.createInstance({
        name: 'showWhitespaceStore',
        driver: DRIVERS,
    });

    Vue.prototype.$hasPermission = (permission, courseId, asMap) => {
        function makeResponse(map) {
            if (typeof permission === 'string') {
                return map[permission];
            } else if (asMap) {
                return map;
            } else {
                return permission.map(p => map[p]);
            }
        }
        if (courseId) {
            return store.dispatch('courses/loadCourses').then(() => {
                const map = store.getters['courses/courses'][courseId].permissions;
                return makeResponse(map);
            });
        } else {
            return Promise.resolve(makeResponse(store.getters['user/permissions']));
        }
    };

    function getUTCEpoch() {
        return moment();
    }

    /* eslint-disable no-new */
    const app = new Vue({
        el: '#app',
        router,
        template: '<App/>',
        components: { App },
        store,

        data() {
            return {
                screenWidth: window.innerWidth,
                smallWidth: 628,
                mediumWidth: 768,
                largeWidth: 992,
                xlargeWidth: 1200,
                // `Now` and `epoch` both contain the current time. They are
                // the same, except that `epoch` is recalculated every second
                // while `now` is set only every minute. We do not want `now`
                // to be updated as often because that would trigger a redraw
                // of the sidebar every second.
                now: moment(),
                epoch: getUTCEpoch(),
            };
        },

        created() {
            window.addEventListener('resize', () => {
                this.screenWidth = window.innerWidth;
            });

            this.$on('cg::root::update-now', () => {
                this.epoch = getUTCEpoch();
                this.now = moment();
            });

            setInterval(() => {
                this.now = moment();
            }, 60000);

            setInterval(() => {
                this.epoch = getUTCEpoch();
            }, 1000);
        },

        computed: {
            $windowWidth() {
                return this.screenWidth;
            },

            $isSmallWindow() {
                return this.screenWidth <= this.smallWidth;
            },

            $isMediumWindow() {
                return this.screenWidth >= this.mediumWidth;
            },

            $isLargeWindow() {
                return this.screenWidth >= this.largeWidth;
            },

            $isXLargeWindow() {
                return this.screenWidth >= this.xlargeWidth;
            },

            isEdge() {
                return window.navigator.userAgent.indexOf('Edge') > -1;
            },

            isSafari() {
                const ua = window.navigator.userAgent;
                // Contains safari and does not contain Chrome as Google Chrome
                // contains Safari and Chrome.
                return ua.indexOf('Safari') > -1 && ua.indexOf('Chrome') < 0;
            },

            $now() {
                return this.now;
            },

            $epoch() {
                return this.epoch;
            },
        },

        watch: {
            isEdge: {
                immediate: true,
                handler() {
                    if (this.isEdge) {
                        document.body.classList.add('cg-edge');
                    }
                },
            },
        },
    });

    // eslint-disable-next-line
    window.__app__ = app;

    // Clear some items in vuex store on CTRL-F5
    document.addEventListener(
        'keydown',
        async event => {
            let isF5;
            if (event.key !== undefined) {
                isF5 = event.key === 'F5';
            } else if (event.keyIdentifier !== undefined) {
                isF5 = event.keyIdentifier === 'F5';
            } else if (event.keyCode !== undefined) {
                isF5 = event.keyCode === 116;
            }

            if (isF5 && (event.ctrlKey || event.shiftKey)) {
                event.preventDefault();
                await app.$store.commit(`user/${mutationTypes.CLEAR_CACHE}`);
                window.location.reload(true);
            }
        },
        true,
    );
});
