<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<ol :class="{ editable: editable, 'lint-whitespace': lintWhitespace, 'show-whitespace': showWhitespace }"
    :start="computedStartLine"
    :style="{
        paddingLeft: noLineNumbers ? 0 : `${3 + Math.log10(computedEndLine) * 2/3}em`,
        listStyle: noLineNumbers ? 'none' : null,
        fontSize: `${fontSize}px`,
    }"
    class="hljs inner-code-viewer"
    @click="addFeedback($event)">

    <li v-for="i in computedEndLine"
        v-if="i - 1 >= computedStartLine - 1 && (i < codeLines.length || codeLines[i - 1] !== '')"
        :key="i - 1"
        class="line"
        :class="{
            'linter-feedback-outer': $userConfig.features.linters && linterFeedback[i - 1 + lineFeedbackOffset],
            'feedback-outer': $utils.getProps(feedback, null, i - 1 + lineFeedbackOffset, 'msg') != null
        }"
        :data-line="i">

        <code v-html="codeLines[i - 1]"/>

        <linter-feedback-area :feedback="linterFeedback[i - 1]"
                              v-if="$userConfig.features.linters && linterFeedback[i - 1] != null"/>

        <feedback-area
            :editing="editing[i - 1]"
            :feedback="feedback[i - 1 + lineFeedbackOffset].msg"
            :author="feedback[i - 1 + lineFeedbackOffset].author"
            :editable="editable"
            :line="i - 1 + lineFeedbackOffset"
            :total-amount-lines="computedEndLine"
            :file-id="fileId"
            :can-use-snippets="canUseSnippets"
            :assignment="assignment"
            :submission="submission"
            @editFeedback="editFeedback"
            @feedbackChange="feedbackChange"
            v-if="showFeedback && $utils.getProps(feedback, null, i - 1 + lineFeedbackOffset, 'msg') !== null"/>
    </li>
    <li class="empty-file"
        v-if="codeLines.length === 1 && codeLines[0] === ''">
        {{ emptyFileMessage }}
    </li>
    <li class="missing-newline"
        v-if="warnNoNewline && computedEndLine === codeLines.length && codeLines[codeLines.length - 1] != ''">
        <icon name="level-up" style="transform: rotate(90deg)"/> Missing newline at the end of file.
    </li>
</ol>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';

import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/level-up';

import FeedbackArea from './FeedbackArea';
import LinterFeedbackArea from './LinterFeedbackArea';

export default {
    name: 'inner-code-viewer',

    props: {
        assignment: {
            type: Object,
            default: null,
        },
        submission: {
            type: Object,
            default: null,
        },
        codeLines: {
            type: Array,
            required: true,
        },
        feedback: {
            type: Object,
            required: true,
        },
        linterFeedback: {
            type: Object,
            default: () => ({}),
        },
        editable: {
            type: Boolean,
            default: false,
        },
        showWhitespace: {
            type: Boolean,
            default: true,
        },
        fileId: {
            type: Number,
            required: true,
        },
        canUseSnippets: {
            type: Boolean,
            default: false,
        },
        startLine: {
            type: Number,
            default: 0,
        },
        endLine: {
            type: Number,
            default: null,
        },
        warnNoNewline: {
            type: Boolean,
            default: true,
        },
        lineFeedbackOffset: {
            type: Number,
            default: 0,
        },
        noLineNumbers: {
            type: Boolean,
            default: false,
        },
        emptyFileMessage: {
            type: String,
            default: 'File is empty.',
        },
    },

    data() {
        return {
            editing: {},
        };
    },

    computed: {
        ...mapGetters('user', {
            currentUserName: 'name',
        }),

        ...mapGetters('pref', ['fontSize']),

        computedStartLine() {
            return Math.max(this.startLine + 1, 1);
        },

        computedEndLine() {
            if (this.endLine === null) {
                return this.codeLines.length;
            }
            return Math.min(this.endLine, this.codeLines.length);
        },

        lintWhitespace() {
            return this.assignment && this.assignment.whitespace_linter;
        },

        showFeedback() {
            return this.assignment != null && this.submission != null;
        },
    },

    components: {
        FeedbackArea,
        LinterFeedbackArea,
        Icon,
    },

    methods: {
        ...mapActions('courses', {
            storeAddFeedbackLine: 'addSubmissionFeedbackLine',
        }),

        async addFeedback(event) {
            if (!this.editable) {
                return;
            }

            const el = event.target.closest('li.line');
            if (!el) return;

            const line = Number(el.getAttribute('data-line')) - 1;

            if (!this.feedback[line] || !this.feedback[line].msg) {
                await this.storeAddFeedbackLine({
                    assignmentId: this.assignment.id,
                    submissionId: this.submission.id,
                    fileId: this.fileId,
                    line: line + this.lineFeedbackOffset,
                    author: { name: this.currentUserName },
                });
            }
            this.$set(this.editing, line, true);

            this.$nextTick(() => {
                const feedbackArea = el.querySelector('.feedback-area textarea');
                if (feedbackArea) {
                    feedbackArea.focus();
                }
            });
        },

        feedbackChange(line) {
            this.$set(this.editing, line - this.lineFeedbackOffset, undefined);
        },

        editFeedback(line) {
            this.$set(this.editing, line - this.lineFeedbackOffset, true);
        },
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

ol {
    margin: 0;
    padding: 0;
    overflow-x: visible;
    background: @linum-bg;
    font-family: monospace;
    font-size: small;

    #app.dark & {
        background: @color-primary-darkest !important;
        color: @color-secondary-text-lighter !important;
    }
}

li {
    position: relative;
    padding-left: 0.75em;
    padding-right: 0.75em;
    cursor: text;

    background-color: lighten(@linum-bg, 1%);
    border-left: 1px solid darken(@linum-bg, 5%);

    #app.dark & {
        background: @color-primary-darker;
        border-left: 1px solid darken(@color-primary-darkest, 5%);
    }

    .inner-code-viewer.editable &,
    #app.dark .inner-code-viewer.editable & {
        &:not(.missing-newline):not(.empty-file):hover {
            cursor: pointer;
            background-color: rgba(0, 0, 0, 0.025);
        }
    }

    &.missing-newline,
    &.empty-file {
        list-style-type: none;
        cursor: default;
        user-select: none;

        svg {
            margin-bottom: -0.125em;
        }
    }
}

code {
    color: @color-secondary-text;
    white-space: pre-wrap;
    font-size: 100%;

    word-wrap: break-word;
    word-break: break-word;
    -ms-word-break: break-all;

    -webkit-hyphens: auto;
    -moz-hyphens: auto;
    -ms-hyphens: auto;
    hyphens: auto;

    #app.dark & {
        color: #839496;
    }
}
</style>


<style lang="less">
@import '~mixins.less';

#app.dark ol.inner-code-viewer .btn:not(.btn-success):not(.btn-danger):not(.btn-warning) {
    background: @color-secondary;

    &.btn-secondary {
        background-color: @color-primary-darker;

        &:hover {
            background: @color-primary-darker;
        }
    }

    &:hover {
        background: darken(@color-secondary, 10%);
    }
}
</style>
