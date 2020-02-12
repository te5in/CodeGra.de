<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<b-alert show v-if="!proxyId && !isMyFile" variant="light" style="overflow: auto;">
    <div>
        <p>
            This file looks like an HTML file. We can render this file, or show its
            source.
        </p>

        <b-button-toolbar justify>
            <submit-button :submit="getIframeSrc" @success="afterGetIframeSrc" variant="outline-danger">
                Render html
            </submit-button>
            <b-btn @click="rejectWarning" variant="primary">
                {{ rejectText }}
            </b-btn>
        </b-button-toolbar>


        <advanced-collapse start-open>
            <b-form-group label-cols="10"
                          horizontal
                          label-for="allow-scripts-iframe"
                          label="Allow JavaScript execution">
                <b-form-radio-group id="allow-scripts-iframe"
                                    v-model="allowScripts"
                                    :options="yesNoOptions" />
            </b-form-group>

            <b-form-group label-cols="10"
                          horizontal
                          label-for="allow-remote-iframe-resources"
                          label="Allow remote resources">
                <b-form-radio-group id="allow-remote-iframe-resources"
                                    v-model="allowRemoteResources"
                                    :options="yesNoOptions" />
            </b-form-group>

            <b-form-group label-cols="10"
                          horizontal
                          label-for="allow-remote-scripts-iframe"
                          label="Allow 'eval' usage and loading of remote JavaScript">
                <b-form-radio-group id="allow-remote-scripts-iframe"
                                    v-model="allowRemoteScripts"
                                    :options="yesNoOptions" />
            </b-form-group>
    </advanced-collapse>
    </div>
</b-alert>
<div v-else class="flex-column d-flex-non-important">
    <b-alert variant="warning" show dismissible
             class="m-0 border-bottom rounded-0">
        Displayed below is a rendered html file,
        <a href="#" @click.capture.prevent.stop="rejectWarning">click here</a> to
        show the source.
    </b-alert>
    <loader v-if="!loaded" page-loader />

    <iframe :src="iframeSrc"
            ref="iframe"
            class="border-0"
            :class=" loaded ? 'flex-grow-1' : ''"
            :style="{ opacity: loaded ? 1 : 0 }"
            @load="onLoad"
            :csp="iframeCsp"
            referrer="no-referrer"
            :sandbox="allowScripts ? 'allow-scripts allow-popups' : 'allow-popups'"/>
</div>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';

import FloatingFeedbackButton from './FloatingFeedbackButton';
import SubmitButton from './SubmitButton';
import CodeViewer from './CodeViewer';
import Loader from './Loader';
import AdvancedCollapse from './AdvancedCollapse';

export default {
    name: 'html-viewer',

    props: {
        assignment: {
            type: Object,
            required: true,
        },
        submission: {
            type: Object,
            required: true,
        },
        file: {
            type: Object,
            required: true,
        },
        fileId: {
            required: true,
        },
        revision: {
            type: String,
            required: true,
        },
        editable: {
            type: Boolean,
            required: false,
        },
        canUseSnippets: {
            type: Boolean,
            required: true,
        },
        showInlineFeedback: {
            type: Boolean,
            default: true,
        },
    },

    data() {
        return {
            proxyId: null,
            loaded: false,

            allowScripts: true,
            allowRemoteResources: true,
            allowRemoteScripts: false,

            yesNoOptions: [{ text: 'yes', value: true }, { text: 'no', value: false }],
        };
    },

    watch: {
        id: {
            immediate: true,
            handler() {
                this.setDefaultOptions();

                if (this.isMyFile) {
                    this.$emit('load');
                    this.getIframeSrc().then(this.afterGetIframeSrc, err => this.$emit('error', err));
                } else {
                    this.$emit('load');
                }
            },
        },
    },

    computed: {
        ...mapGetters('feedback', ['getFeedback']),
        ...mapGetters('user', { myId: 'id' }),
        ...mapGetters('autotest', {
            allAutoTests: 'tests',
        }),

        autoTest() {
            return this.allAutoTests[this.assignment.auto_test_id];
        },

        autoTestRun() {
            return this.$utils.getProps(this.autoTest, null, 'runs', 0);
        },

        id() {
            return this.file ? this.file.id : -1;
        },

        line() {
            return 0;
        },

        isStudent() {
            return this.$utils.getProps(this.assignment, false, 'course', 'isStudent');
        },

        feedback() {
            return this.$utils.getProps(
                this.submission,
                {},
                'feedback',
                'user',
                this.id,
                this.line,
            );
        },

        currentPath() {
            const arr = [];
            let cur = this.file;
            while (cur.parent != null) {
                arr.push(cur.name);
                cur = cur.parent;
            }
            if (this.revision === 'autotest') {
                arr.pop();
            }
            arr.reverse();
            return arr.join('/');
        },

        iframeSrc() {
            if (UserConfig.proxyUrl) {
                return `${UserConfig.proxyUrl}/${this.proxyId}/${this.currentPath}`;
            } else {
                const { host, protocol } = window.location;
                return `${protocol}//${host}/api/v1/proxy/${this.proxyId}/${this.currentPath}`;
            }
        },

        iframeCsp() {
            return "default-src 'self'";
        },

        hasFeedback() {
            if (!this.showInlineFeedback || this.revision !== 'student') {
                return false;
            }
            const allFeedback = this.getFeedback(this.assignment.id, this.submission.id);
            const fileId = this.fileId;

            if (!allFeedback) {
                return false;
            }

            const feedback = allFeedback.user[fileId] || {};
            return Object.keys(feedback).length > 0;
        },

        rejectText() {
            const base = 'Show source';
            if (this.hasFeedback && this.editable) {
                return `${base}, and display and give line feedback`;
            } else if (this.hasFeedback) {
                return `${base}, and display line feedback`;
            } else if (this.editable) {
                return `${base}, and give line feedback`;
            } else {
                return `${base}`;
            }
        },

        isMyFile() {
            return this.myId === this.submission.userId;
        },
    },

    destroyed() {
        this.$root.$emit('cg::root::unfade-selected-file');
    },

    methods: {
        ...mapActions('code', {
            storeLoadCode: 'loadCode',
        }),

        setDefaultOptions() {
            this.proxyId = null;
            this.loaded = false;
            this.allowScripts = true;
            this.allowRemoteResources = true;
            this.allowRemoteScripts = this.isMyFile;
        },

        getIframeSrc() {
            let url;
            if (this.revision === 'autotest') {
                let curFile = this.file;
                while (curFile && curFile.autoTestSuiteId == null) {
                    curFile = curFile.parent;
                }
                const suiteId = curFile.autoTestSuiteId;
                const resultId = this.autoTestRun.findResultBySubId(this.submission.id).id;
                url = `/api/v1/auto_tests/${this.assignment.auto_test_id}/runs/${this.autoTestRun.id}/results/${resultId}/suites/${suiteId}/proxy`;
            } else {
                url = `/api/v1/submissions/${this.submission.id}/proxy`;
            }

            return this.$http.post(url, {
                allow_remote_resources: this.allowRemoteResources,
                allow_remote_scripts: this.allowRemoteScripts,
                teacher_revision: this.revision === 'teacher',
            }).catch(
                err => {
                    if (this.isMyFile) {
                        this.$emit(
                            'error',
                            `An error occured while rendering the HTML: ${this.$utils.getErrorMessage(
                                err,
                            )}.`,
                        );
                    }
                    throw err;
                },
            );
        },

        afterGetIframeSrc({ data }) {
            this.proxyId = data.id;
            this.$root.$emit('cg::root::fade-selected-file');
        },

        rejectWarning() {
            this.proxyId = null;
            this.$emit('force-viewer', CodeViewer);
        },

        onLoad() {
            this.loaded = true;
        },
    },

    components: {
        FloatingFeedbackButton,
        SubmitButton,
        Loader,
        AdvancedCollapse,
    },
};
</script>

<style lang="less">
.html-viewer .d-flex-non-important {
    display: flex;
}
</style>
