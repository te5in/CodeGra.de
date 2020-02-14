<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<b-alert v-if="!confirmedLines && (computedEndLine - computedStartLine) > maxLines"
         show
         variant="warning"
         class="mb-0 rounded">
    This file has {{ innerCodeLines.length - (hasMissingNewline ? 0 : 1) }} lines. Rendering it may
    cause the page to freeze or other issues. Do you want to render this file?

    <b-button-toolbar justify class="mt-2">
        <b-button @click.prevent.stop="renderNextLines(innerCodeLines.length)"
                  variant="warning"
                  class="d-block">
            Render all lines
        </b-button>

        <b-button @click.prevent.stop="renderNextLines(maxLines)"
                  variant="primary"
                  class="d-block">
            Render first {{ maxLines }} lines
        </b-button>
    </b-button-toolbar>
</b-alert>

<div v-else class="inner-code-viewer">
    <ol :class="{
            editable: canGiveFeedback,
            'lint-whitespace': lintWhitespace,
            'show-whitespace': showWhitespace,
         }"
        :start="computedStartLine"
        :style="{
            paddingLeft: lineNumberWidth,
            listStyle: noLineNumbers ? 'none' : null,
            fontSize: `${fontSize}px`,
            cursor: canGiveFeedback ? cursorType : 'text',
        }"
        class="hljs lines"
        @mousedown="dragStart"
        @mouseup="dragStop">

        <li v-for="i in computedEndLine"
            v-if="i - 1 >= computedStartLine - 1 && (i < innerCodeLines.length || innerCodeLines[i - 1] !== '')"
            :key="i"
            class="line"
            :class="{
                'linter-feedback-outer': $userConfig.features.linters && linterFeedback[i - 1 + lineFeedbackOffset],
                'feedback-outer': showFeedback && $utils.getProps(feedback, null, i - 1 + lineFeedbackOffset, 'msg') != null
            }"
            :data-line="i">

            <code v-html="innerCodeLines[i - 1]" />

            <linter-feedback-area :feedback="linterFeedback[i - 1]"
                                  v-if="$userConfig.features.linters && linterFeedback[i - 1] != null"/>

            <feedback-area
                :key="i"
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
                v-if="showFeedback && $utils.getProps(feedback, null, i - 1 + lineFeedbackOffset) != null"/>
        </li>
        <li class="empty-file"
            v-if="innerCodeLines.length === 1 && innerCodeLines[0] === ''">
            {{ emptyFileMessage }}
        </li>
        <li class="missing-newline"
            v-if="showMissingNewline">
            <icon name="level-up" class="missing-newline-icon"/> Missing newline at the end of file.
        </li>
    </ol>

    <div class="render-next-lines"
         v-if="confirmedLines && !atEndOfFile">
        <div class="left"
             :style="{ flex: `0 0 ${lineNumberWidth}`, fontSize: `${fontSize}px` }">
            <loader class="float-right" :scale="1" v-if="showLinesLoader" />
        </div>
        <b-button-toolbar class="right py-1 justify-content-center">
            <b-button class="mr-2"
                      size="sm"
                      :variant="remainingLines > nextRenderedLines ? 'warning' : 'primary'"
                      :disabled="showLinesLoader"
                      @click="renderNextLines(innerCodeLines.length - confirmedLines)">
                Show remaining {{ remainingLines }} line{{ remainingLines === 1 ? '' : 's' }}
            </b-button>
            <b-button size="sm"
                      variant="primary"
                      :disabled="showLinesLoader"
                      @click="renderNextLines(maxLines)"
                      v-if="remainingLines > nextRenderedLines">
                Show next {{ nextRenderedLines }} line{{ nextRenderedLines === 1 ? '' : 's' }}
            </b-button>
        </b-button-toolbar>
    </div>
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
        showInlineFeedback: {
            type: Boolean,
            default: true,
        },
        fileId: {
            type: String,
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
            cursorType: 'pointer',
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

        canGiveFeedback() {
            if (this.canGiveFeedback) {
                this.cursorType = 'pointer';
            }
        },
    },

    computed: {
        ...mapGetters('user', {
            myId: 'id',
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

        canGiveFeedback() {
            return this.editable && this.showInlineFeedback;
        },

        showFeedback() {
            return this.assignment != null && this.submission != null && this.showInlineFeedback;
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

        remainingLines() {
            let remaining = this.innerCodeLines.length - this.confirmedLines;

            if (!this.hasMissingNewline) {
                remaining -= 1;
            }

            return remaining;
        },

        nextRenderedLines() {
            return Math.min(this.maxLines, this.remainingLines);
        },

        lineNumberWidth() {
            return this.noLineNumbers
                ? 0
                : `${3 + Math.log10(this.innerCodeLines.length) * 2 / 3}em`;
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
        ...mapActions('feedback', {
            storeAddFeedbackLine: 'addFeedbackLine',
        }),

        removeDragHandler() {
            this.$el.removeEventListener('mousemove', this.dragMove);
        },

        async addFeedback(event) {
            if (!this.canGiveFeedback) {
                return;
            }

            const el = event.target.closest('li.line');
            if (!el) {
                return;
            }

            const line = Number(el.getAttribute('data-line')) - 1;
            const feedbackLine = line + this.lineFeedbackOffset;

            // We can never be editing this line when there is no feedback to
            // edit. So this mapping is simply outdated. This happens because we
            // do not reset the editing back to `false` when deleting
            // feedback. We do not do this because when deleting a line of
            // feedback, the line is deleted from the store. This means the
            // component will stop existing, so it is impossible for it to emit
            // a `deleted` event.
            if (this.editing[line] && this.feedback[feedbackLine] != null) {
                return;
            }

            if (!this.feedback[feedbackLine] || !this.feedback[feedbackLine].msg) {
                await this.storeAddFeedbackLine({
                    assignmentId: this.assignment.id,
                    submissionId: this.submission.id,
                    fileId: this.fileId,
                    line: feedbackLine,
                    author: { id: this.myId },
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
            this.$delete(this.editing, line - this.lineFeedbackOffset);
        },

        editFeedback(line) {
            this.$set(this.editing, line - this.lineFeedbackOffset, true);
        },

        dragStart(event) {
            if (event.button === 0 && this.canGiveFeedback) {
                this.dragEvent = event;
                this.$el.addEventListener('mousemove', this.dragMove);
            }
        },

        dragMove(event) {
            this.cursorType = this.movedTooFar(event) ? 'text' : 'cursor';
        },

        movedTooFar(currentEvent) {
            const firstEvent = this.dragEvent;
            if (!firstEvent) {
                return false;
            }

            let dx = 0;
            let dy = 0;

            if (firstEvent.clientX != null) {
                dx = Math.abs(currentEvent.clientX - firstEvent.clientX);
            }
            if (firstEvent.clientY != null) {
                dy = Math.abs(currentEvent.clientY - firstEvent.clientY);
            }

            return dx + dy >= 1;
        },

        dragStop(event) {
            if ((this.dragEvent != null || event.button === 0) && !this.movedTooFar(event)) {
                this.addFeedback(event);
            }

            this.dragEvent = null;
            this.cursorType = 'pointer';
            this.removeDragHandler();
        },

        async renderNextLines(nLines) {
            this.showLinesLoader = true;

            await this.$afterRerender();

            this.confirmedLines += nLines;
            this.showLinesLoader = false;
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

    background-color: lighten(@linum-bg, 1%);
    border-left: 1px solid darken(@linum-bg, 5%);

    #app.dark & {
        background: @color-primary-darker;
        border-left: 1px solid darken(@color-primary-darkest, 5%);
    }

    ol.lines.editable &,
    #app.dark ol.lines.editable & {
        &.line:hover {
            background-color: rgba(0, 0, 0, 0.025);
        }
    }

    &.missing-newline,
    &.empty-file {
        list-style-type: none;
        cursor: default;
        user-select: none;

        .fa-icon {
            transform: rotate(90deg);

            &.missing-newline-icon {
                transform: translateY(-2px) rotate(90deg);
            }
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
        color: rgb(131, 148, 150);
    }
}

.render-next-lines {
    display: flex;

    .left {
        align-self: stretch;
        display: flex;
        justify-content: center;
        align-items: center;
    }

    .right {
        flex: 1 1 auto;
        border-top: 1px solid darken(@linum-bg, 5%);

        #app.dark & {
            border-top: 1px solid darken(@color-primary-darkest, 5%);
        }
    }
}
</style>

<style lang="less">
@import '~mixins.less';

#app.dark ol.lines .btn:not(.btn-success):not(.btn-danger):not(.btn-warning) {
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
