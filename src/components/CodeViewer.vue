<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="code-viewer" :class="{ editable }">
    <inner-code-viewer
        :assignment="assignment"
        :submission="submission"
        :code-lines="codeLines"
        :feedback="feedback"
        :linter-feedback="linterFeedback"
        :show-whitespace="showWhitespace"
        :editable="feedbackEditable"
        :can-use-snippets="canUseSnippets"
        :file-id="fileId"/>
</div>
</template>

<script>
import { listLanguages } from 'highlightjs';
import { mapGetters, mapActions } from 'vuex';

import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/plus';
import 'vue-awesome/icons/cog';

import { cmpNoCase, highlightCode } from '@/utils';
import '@/polyfills';
import decodeBuffer from '@/utils/decode';

import InnerCodeViewer from './InnerCodeViewer';
import Toggle from './Toggle';

export default {
    name: 'code-viewer',

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
        editable: {
            type: Boolean,
            default: false,
        },
        language: {
            type: String,
            default: 'Default',
        },
        revision: {
            type: String,
            required: true,
        },
        canUseSnippets: {
            type: Boolean,
            required: true,
        },
        showWhitespace: {
            type: Boolean,
            required: true,
        },
    },

    computed: {
        ...mapGetters('pref', ['fontSize']),

        feedbackEditable() {
            return this.editable && this.studentMode;
        },

        fileId() {
            return this.file.id || this.file.ids[0] || this.file.ids[1];
        },

        extension() {
            const fileParts = this.file.name.split('.');
            return fileParts.length > 1 ? fileParts[fileParts.length - 1] : null;
        },

        studentMode() {
            return this.revision === 'student';
        },

        isLargeFile() {
            return this.rawCodeLines && this.rawCodeLines.length > 5000;
        },

        feedback() {
            const feedback = this.submission.feedback;
            const fileId = this.fileId;

            if (!feedback || !this.studentMode) {
                return {};
            }

            return feedback.user[fileId] || {};
        },

        linterFeedback() {
            const feedback = this.submission.feedback;
            const fileId = this.fileId;

            if (!feedback || !this.studentMode) {
                return {};
            }

            return feedback.linter[fileId] || {};
        },
    },

    data() {
        const languages = listLanguages();
        languages.push('plain');
        languages.sort(cmpNoCase);
        languages.unshift('Default');

        return {
            rawCodeLines: [],
            codeLines: [],
            selectedLanguage: 'Default',
            languages,
            canSeeAssignee: false,
        };
    },

    mounted() {
        Promise.all([
            this.loadCodeWithSettings(),
            this.$hasPermission('can_see_assignee', this.assignment.course.id),
        ]).then(([, assignee]) => {
            this.canSeeAssignee = assignee;
        });
    },

    watch: {
        fileId(newId, oldId) {
            if (newId != null && (oldId == null || newId !== oldId)) {
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
        ...mapActions('code', {
            storeLoadCode: 'loadCode',
        }),

        loadCodeWithSettings() {
            return this.$hlanguageStore.getItem(`${this.file.id}`).then(lang => {
                if (lang !== null) {
                    this.$emit('language', lang);
                    this.selectedLanguage = lang;
                } else {
                    this.selectedLanguage = 'Default';
                }

                return this.getCode();
            });
        },

        async getCode() {
            this.codeLines = [];
            this.rawCodeLines = [];
            await this.$afterRerender();

            let code;

            try {
                code = await this.storeLoadCode(this.fileId);
            } catch (e) {
                this.$emit('error', e);
                return;
            }

            try {
                code = decodeBuffer(code);
            } catch (e) {
                this.$emit('error', 'This file cannot be displayed');
                return;
            }

            this.rawCodeLines = code.split('\n');

            this.highlightCode(this.selectedLanguage);
            this.$emit('load');
        },

        // Highlight this.codeLines.
        highlightCode(language) {
            const lang = language === 'Default' ? this.extension : language;
            this.codeLines = highlightCode(this.rawCodeLines, lang);
        },
    },

    components: {
        Icon,
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
</style>
