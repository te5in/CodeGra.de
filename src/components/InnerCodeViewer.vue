<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<b-alert v-if="!confirmedLines && innerCodeLines.length > maxLines"
         show
         variant="warning"
         class="mb-0 rounded">
    This file has {{ innerCodeLines.length }} lines. Rendering it may cause the page to freeze or other
    issues. Do you want to render this file?

    <b-button-toolbar justify class="mt-2">
        <b-button @click.prevent.stop="confirmedLines = innerCodeLines.length"
                  variant="warning"
                  class="d-block">
            Render all lines
        </b-button>

        <b-button @click.prevent.stop="confirmedLines = maxLines"
                  variant="primary"
                  class="d-block">
            Render first {{ maxLines }} lines
        </b-button>
    </b-button-toolbar>
</b-alert>

<div v-else>
    <ol :class="{
            editable: editable,
            'lint-whitespace': lintWhitespace,
            'show-whitespace': showWhitespace,
         }"
        :start="computedStartLine"
        :style="{
            paddingLeft: noLineNumbers ? 0 : `${3 + Math.log10(computedEndLine) * 2/3}em`,
            listStyle: noLineNumbers ? 'none' : null,
            fontSize: `${fontSize}px`,
        }"
        class="hljs inner-code-viewer"
        @mousedown="dragStart"
        @mouseup="dragStop">

        <li v-for="i in computedEndLine"
            v-if="i - 1 >= computedStartLine - 1 && (innerCodeLines[i - 1] !== '')"
            :key="i"
            class="line"
            :class="{
                'linter-feedback-outer': $userConfig.features.linters && linterFeedback[i - 1 + lineFeedbackOffset],
                'feedback-outer': $utils.getProps(feedback, null, i - 1 + lineFeedbackOffset, 'msg') != null
            }"
            :data-line="i">

            <code v-html="innerCodeLines[i - 1]" />

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
            v-if="innerCodeLines.length === 1 && innerCodeLines[0] === ''">
            {{ emptyFileMessage }}
        </li>
        <li class="missing-newline"
            v-if="showMissingNewline">
            <icon name="level-up" style="transform: rotate(90deg)"/> Missing newline at the end of file.
        </li>
    </ol>

    <b-button-toolbar v-if="confirmedLines && !atEndOfFile"
                      class="justify-content-center">
        <b-button @click="renderNextLines(maxLines)"
                  class="my-1">
            <loader v-if="showLinesLoader" :scale="1.5" />
            <span v-else>
                Show next {{ nextRenderedLines }} line{{ nextRenderedLines === 1 ? '' : 's' }}
            </span>
        </b-button>
    </b-button-toolbar>
</div>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';

import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/level-up';

import Loader from './Loader';
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
        maxLines: {
            type: Number,
            default: UserConfig.maxLines,
        },
    },

    data() {
        return {
            editing: {},
            dragEvent: null,
            confirmedLines: false,
            showLinesLoader: false,
            innerCodeLines: [],
        };
    },

    watch: {
        fileId() {
            this.confirmedLines = false;
        },

        codeLines: {
            immediate: true,
            handler() {
                this.innerCodeLines = Object.freeze(
                    Object.preventExtensions(this.codeLines.map(x => x)),
                );
            },
        },
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
            let end = this.innerCodeLines.length;

            if (this.confirmedLines !== false) {
                end = Math.min(end, this.confirmedLines);
            }

            if (this.endLine !== null) {
                end = Math.min(end, this.endLine);
            }

            return end;
        },

        lintWhitespace() {
            return this.assignment && this.assignment.whitespace_linter;
        },

        showFeedback() {
            return this.assignment != null && this.submission != null;
        },

        atEndOfFile() {
            return this.computedEndLine >= this.innerCodeLines.length;
        },

        hasMissingNewline() {
            return this.innerCodeLines[this.innerCodeLines.length - 1] !== '';
        },

        showMissingNewline() {
            return this.warnNoNewline && this.atEndOfFile && this.hasMissingNewline;
        },

        nextRenderedLines() {
            let remaining = this.innerCodeLines.length - this.confirmedLines;

            if (!this.hasMissingNewline) {
                remaining -= 1;
            }

            return Math.min(this.maxLines, remaining);
        },
    },

    components: {
        Icon,
        Loader,
        FeedbackArea,
        LinterFeedbackArea,
    },

    destroyed() {
        this.removeDragHandler();
    },

    methods: {
        ...mapActions('submissions', {
            storeAddFeedbackLine: 'addSubmissionFeedbackLine',
        }),

        removeDragHandler() {
            this.$el.removeEventListener('mousemove', this.dragMove);
        },

        async addFeedback(event) {
            if (!this.editable) {
                return;
            }

            const el = event.target.closest('li.line');
            if (!el) return;

            const line = Number(el.getAttribute('data-line')) - 1;
            const feedbackLine = line + this.lineFeedbackOffset;

            if (this.editing[line]) {
                return;
            }

            if (!this.feedback[feedbackLine] || !this.feedback[feedbackLine].msg) {
                await this.storeAddFeedbackLine({
                    assignmentId: this.assignment.id,
                    submissionId: this.submission.id,
                    fileId: this.fileId,
                    line: feedbackLine,
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

        dragStart() {
            this.$el.addEventListener('mousemove', this.dragMove);
        },

        dragMove(event) {
            if (this.dragEvent == null) {
                this.dragEvent = event;
            }
        },

        dragStop(event) {
            let dx = 0;
            let dy = 0;

            if (this.dragEvent != null) {
                dx = Math.abs(event.clientX - this.dragEvent.clientX);
                dy = Math.abs(event.clientY - this.dragEvent.clientY);
            }

            if (!this.dragEvent || dx + dy < 1) {
                this.addFeedback(event);
            }

            this.removeDragHandler();
            this.dragEvent = null;
        },

        async renderNextLines(nLines) {
            // Use of multiple nextTicks and the timeout here is intentional and required
            // for a correct ordering of events: without them the loader would not be shown
            // while rendering the next lines.

            this.showLinesLoader = true;

            await this.$nextTick();
            setTimeout(async () => {
                this.confirmedLines += nLines;
                await this.$nextTick();
                this.showLinesLoader = false;
            }, 0);
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
