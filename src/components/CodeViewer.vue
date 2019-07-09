<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<b-alert class="error" variant="danger" show v-if="error">
    <div v-html="error"/>
</b-alert>
<loader class="text-center" v-else-if="loading"/>
<div class="code-viewer form-control" :class="{ editable }" v-else>
    <div class="scroller">
        <inner-code-viewer
            :assignment="assignment"
            :code-lines="codeLines"
            :feedback="diffMode ? {} : feedback"
            :linter-feedback="diffMode ? {} : linterFeedback"
            :show-whitespace="showWhitespace"
            @set-feedback="$set(feedback, $event.line, $event)"
            :font-size="fontSize"
            :editable="editable && !diffMode"
            :can-use-snippets="canUseSnippets"
            :file-id="file.id"/>
    </div>
</div>
</template>

<script>
import { listLanguages } from 'highlightjs';

import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/plus';
import 'vue-awesome/icons/cog';

import { cmpNoCase, highlightCode } from '@/utils';
import '@/polyfills';
import decodeBuffer from '@/utils/decode';

import InnerCodeViewer from './InnerCodeViewer';
import Loader from './Loader';
import Toggle from './Toggle';

export default {
    name: 'code-viewer',

    props: {
        assignment: {
            type: Object,
            default: null,
        },
        submission: {
            type: Object,
            default: null,
        },
        file: {
            type: Object,
            default: null,
        },
        editable: {
            type: Boolean,
            default: false,
        },
        tree: {
            type: Object,
            default: {},
        },
        language: {
            type: String,
            default: 'Default',
        },
        fontSize: {
            type: Number,
            default: 12,
        },
        showWhitespace: {
            type: Boolean,
            default: true,
        },
        canUseSnippets: {
            type: Boolean,
            required: true,
        },
    },

    computed: {
        extension() {
            const fileParts = this.file.name.split('.');
            return fileParts.length > 1 ? fileParts[fileParts.length - 1] : null;
        },

        diffMode() {
            return this.$route.query.revision === 'diff';
        },

        isLargeFile() {
            return this.rawCodeLines && this.rawCodeLines.length > 5000;
        },
    },

    data() {
        const languages = listLanguages();
        languages.push('plain');
        languages.sort(cmpNoCase);
        languages.unshift('Default');
        return {
            code: '',
            rawCodeLines: [],
            codeLines: [],
            loading: true,
            editing: {},
            feedback: {},
            linterFeedback: {},
            error: false,
            darkMode: true,
            selectedLanguage: 'Default',
            languages,
            canSeeAssignee: false,
        };
    },

    mounted() {
        Promise.all([
            this.loadCodeWithSettings(false),
            this.$hasPermission('can_see_assignee', this.assignment.course.id),
        ]).then(([, assignee]) => {
            this.loading = false;
            this.canSeeAssignee = assignee;
        });
    },

    watch: {
        file(f, oldF) {
            if (!f) {
                return;
            }
            if (!oldF || f.id !== oldF.id) {
                this.loadCodeWithSettings();
            }
        },

        language(lang) {
            if (this.selectedLanguage === lang) {
                return;
            }
            this.selectedLanguage = lang;
            if (!this.isLargeFile) {
                this.highlightCode(lang);
            }
        },
    },

    methods: {
        loadCodeWithSettings(setLoading = true) {
            return this.$hlanguageStore.getItem(`${this.file.id}`).then(val => {
                if (val !== null) {
                    this.$emit('new-lang', val);
                    this.selectedLanguage = val;
                } else {
                    this.selectedLanguage = 'Default';
                }
                return this.getCode(setLoading);
            });
        },

        getCode(setLoading = true) {
            if (setLoading) this.loading = true;
            const error = [];
            this.error = '';

            const fileId = this.file.id || this.file.ids[0] || this.file.ids[1];

            // Split in two promises so that highlighting can begin before we
            // have feedback as this is not needed anyway.
            return Promise.all([
                this.$http
                    .get(`/api/v1/code/${fileId}`, {
                        responseType: 'arraybuffer',
                    })
                    .then(
                        code => {
                            try {
                                this.code = decodeBuffer(code.data);
                            } catch (e) {
                                error.push('This file cannot be displayed');
                                return;
                            }
                            this.rawCodeLines = this.code.split('\n');

                            this.highlightCode(this.selectedLanguage);
                        },
                        ({ response: { data: { message } } }) => {
                            error.push(this.$utils.htmlEscape(message));
                        },
                    ),

                Promise.all([
                    this.$http.get(`/api/v1/code/${fileId}?type=feedback`),
                    UserConfig.features.linters
                        ? this.$http.get(`/api/v1/code/${fileId}?type=linter-feedback`)
                        : Promise.resolve({ data: {} }),
                ]).then(
                    ([feedback, linterFeedback]) => {
                        this.linterFeedback = linterFeedback.data;
                        this.feedback = feedback.data;
                    },
                    ({ response: { data: { message } } }) => {
                        error.push(this.$utils.htmlEscape(message));
                    },
                ),
            ]).then(() => {
                this.error = error.join('<br>');
                if (setLoading) {
                    this.loading = false;
                }
                this.$emit('load');
            });
        },

        // Highlight this.codeLines.
        highlightCode(language) {
            const lang = language === 'Default' ? this.extension : language;
            this.codeLines = highlightCode(this.rawCodeLines, lang);
        },

        // Given a file-tree object as returned by the API, generate an
        // object with file-paths as keys and file-ids as values and an
        // array of file-paths. All // possible paths to a file will be
        // included. E.g. if file `a/b/c` has id 3, the object shall
        // contain the following keys: { 'a/b/c': 3, 'b/c': 3, 'c': 3 }.
        // Longer paths to the same file shall come before shorter paths
        // in the array, so the matching will prefer longer paths.
        flattenFileTree(tree, prefix = []) {
            const fileIds = {};
            const filePaths = [];
            if (!tree || !tree.entries) {
                return [fileIds, filePaths];
            }
            tree.entries.forEach(f => {
                if (f.entries) {
                    const [dirIds, dirPaths] = this.flattenFileTree(f, prefix.concat(f.name));
                    Object.assign(fileIds, dirIds);
                    filePaths.push(...dirPaths);
                } else {
                    const path = prefix.concat(f.name).join('/');
                    let i = 0;
                    do {
                        const spath = path.substr(i);
                        filePaths.push(spath);
                        fileIds[path.substr(i)] = f.id || f.ids[0] || f.ids[1];
                        i = path.indexOf('/', i + 1) + 1;
                    } while (i > 0);
                }
            });
            return [fileIds, filePaths];
        },
    },

    components: {
        Icon,
        Loader,
        Toggle,
        InnerCodeViewer,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.code-viewer {
    position: relative;
    padding: 0;
    background: #f8f8f8;

    #app.dark & {
        background: @color-primary-darker;
    }
}

.scroller {
    width: 100%;
    height: 100%;
    overflow-x: auto;
    overflow-y: auto;
}

.loader {
    margin-top: 2.5em;
    margin-bottom: 3em;
}
</style>
