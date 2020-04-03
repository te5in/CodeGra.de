<template>
<b-input-group
    class="snippetable-input"
    :style="{ 'margin-bottom': notSnippetsAbsoluteBelow && !showSnippetsAbove ?
            '11em' :
            undefined }">
    <div style="flex: 1; position: relative;">
        <b-card class="snippet-list-wrapper rounded"
                :class="{ 'snippets-above': showSnippetsAbove }"
                v-if="possibleSnippets.length > 0">
            <span slot="header"
                  class="snippet-header">Snippets (press <kbd>Tab</kbd> to select the next item)</span>
            <ul :class="{ 'snippet-list': true, inline: line + 6 >= totalAmountLines, }">
                <li class="snippet-item cursor-pointer"
                    v-for="snippet, i in possibleSnippets"
                    :class="{ selected: snippetIndexSelected === i }"
                    ref="snippets"
                    :key="`snippet-key:${snippet.key}:${snippet.course}`"
                    @click.capture.stop.prevent="onClickSnippet(i)">
                    <span v-if="snippet.course" class="snippet-icon"><icon :scale="0.9" name="book"/></span>
                    <span v-else class="snippet-icon"><icon :scale="0.9" name="user-circle-o"/></span>
                    <span>{{ snippet.key }}</span>
                    <span>- {{ snippet.value }}</span>
                </li>
            </ul>
        </b-card>
        <textarea ref="field"
                  v-model="valueCopy"
                  class="form-control editable-feedback-area"
                  :disabled="feedbackDisabled"
                  @keydown.esc.prevent="stopSnippets"
                  @keydown.exact.tab.prevent="maybeSelectNextSnippet(false)"
                  @keydown.exact.shift.tab.prevent="maybeSelectNextSnippet(true)"
                  @keydown="beforeKeyPress"
                  @keyup="updatePossibleSnippets"
                  @keydown.ctrl.enter.prevent="onCtrlEnter"/>
    </div>
    <slot/>
</b-input-group>
</template>


<script>
import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/user-circle-o';
import 'vue-awesome/icons/book';

import { mapActions, mapGetters } from 'vuex';

function lastWhiteSpace(str, start) {
    let i = start;
    for (; i > -1; i--) {
        const val = str[i];
        if (val === ' ' || val === '\n' || val === '\t') {
            return i;
        }
    }
    return -1;
}

export default {
    name: 'snippetable-input',

    props: {
        forceSnippetsAbove: {
            type: Boolean,
            default: false,
        },

        value: {
            type: String,
            required: true,
        },

        line: {
            type: Number,
            required: true,
        },

        totalAmountLines: {
            type: Number,
            required: true,
        },

        bounceTime: {
            type: Number,
            required: true,
        },

        feedbackDisabled: {
            type: Boolean,
            required: true,
        },

        canUseSnippets: {
            type: Boolean,
            required: true,
        },

        minInitialHeight: {
            type: Number,
            default: null,
        },

        maxInitialHeight: {
            type: Number,
            default: null,
        },
    },

    data() {
        return {
            possibleSnippets: [],
            valueCopy: this.value,
            ignoreSnippets: null,
            snippetIndexSelected: null,
        };
    },

    mounted() {
        this.$nextTick(() => {
            let wantedHeight = this.$refs.field.scrollHeight + 5;
            if (this.maxInitialHeight != null && this.maxInitialHeight < wantedHeight) {
                wantedHeight = this.maxInitialHeight;
            }

            if (this.minInitialHeight != null && this.minInitialHeight > wantedHeight) {
                wantedHeight = this.minInitialHeight;
            }
            this.$refs.field.setAttribute(
                'style',
                `height: ${wantedHeight}px;`,
            );
        });
    },

    watch: {
        valueCopy() {
            this.emitInut();
        },

        canUseSnippets: {
            immediate: true,
            async handler() {
                if (this.canUseSnippets) {
                    this.loadedSnippets = false;
                    await this.maybeRefreshSnippets();
                }
                this.loadedSnippets = true;
            },
        },

        value() {
            this.valueCopy = this.value;
        },

        async snippetIndexSelected(_, oldVal) {
            // eslint-disable-next-line
            let [start, end] = this.snippetBound;
            let value;

            if (this.snippetIndexSelected === null) {
                if (this.selectedSnippet === null) {
                    return;
                }
                // In this case we need to reset the field to its original value
                this.selectedSnippet = null;
                value = this.snippetOldKey;
                const oldSnip = this.possibleSnippets[oldVal];
                if (oldSnip != null) {
                    start = Math.max(0, end - oldSnip.value.length);
                }

                // Scroll next element in to view again
                const el = this.$refs.snippets[oldVal === 0 ? this.$refs.snippets.length - 1 : 0];
                if (el && el.scrollIntoView && !(this.$root.isEdge || this.$root.isSafari)) {
                    el.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'smooth' });
                }
            } else {
                const newSnip = this.possibleSnippets[this.snippetIndexSelected];
                if (
                    !newSnip ||
                    (this.selectedSnippet != null &&
                        newSnip.key === this.selectedSnippet.key &&
                        newSnip.course === this.selectedSnippet.course)
                ) {
                    return;
                }

                [1, 0].forEach(i => {
                    const el = this.$refs.snippets[this.snippetIndexSelected + i];
                    if (el && el.scrollIntoView && !(this.$root.isEdge || this.$root.isSafari)) {
                        el.scrollIntoView({
                            block: 'nearest',
                            inline: 'nearest',
                            behavior: 'smooth',
                        });
                    }
                });

                this.selectedSnippet = newSnip;
                if (oldVal === null) {
                    this.snippetOldKey = this.valueCopy.slice(start, end) || '';
                } else {
                    const oldSnip = this.possibleSnippets[oldVal];
                    start = end - oldSnip.value.length;
                }
                ({ value } = newSnip);
            }

            this.valueCopy =
                this.valueCopy.slice(0, start) + value + this.valueCopy.slice(end);

            await this.$nextTick();
            const el = this.$refs.field;
            if (el) {
                el.focus();
                el.setSelectionRange(start + value.length, start + value.length);
            }
        },

    },

    computed: {
        ...mapGetters({
            snippets: 'user/snippets',
            nameCurrentUser: 'user/name',
            findUserSnippetsByPrefix: 'user/findSnippetsByPrefix',
        }),

        snippetBound() {
            if (!this.valueCopy) {
                return [0, 0];
            }
            const selectionEnd = this.$refs.field.selectionEnd;

            const spaceIndex = lastWhiteSpace(this.valueCopy, selectionEnd - 1) + 1;
            if (this.ignoreSnippets != null && this.ignoreSnippets !== spaceIndex) {
                this.ignoreSnippets = null;
            }
            return [spaceIndex, selectionEnd];
        },

        notSnippetsAbsoluteBelow() {
            return this.possibleSnippets.length && this.line + 6 >= this.totalAmountLines;
        },

        showSnippetsAbove() {
            return this.forceSnippetsAbove || (this.notSnippetsAbsoluteBelow && this.line > 6);
        },
    },

    methods: {
        ...mapActions('user', {
            maybeRefreshSnippets: 'maybeRefreshSnippets',
        }),

        async focus() {
            const el = this.$refs.field;
            if (el) {
                el.focus();
                // Put the cursor at the end of the text (Safari puts it at the
                // start for some reason...
                await this.$afterRerender();
                el.setSelectionRange(el.value.length, el.value.length);
            }
        },

        beforeKeyPress(event) {
            if (
                (event.key === 'Backspace' ||
                    event.keyIdentifier === 'Backspace' ||
                    event.keyCode === 8) &&
                (event.selectionStart !== event.selectionEnd || this.snippetIndexSelected !== null)
            ) {
                event.preventDefault();
                this.snippetIndexSelected = null;
            } else if (
                (event.key === 'Enter' ||
                    event.keyIdentifier === 'Enter' ||
                    event.keyCode === 13) &&
                this.snippetIndexSelected !== null
            ) {
                event.preventDefault();
                this.confirmSnippet();
            }
        },

        stopSnippets(event) {
            if (!this.possibleSnippets.length) {
                return;
            }

            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();
            this.snippetIndexSelected = null;
            this.$nextTick().then(() => {
                [this.ignoreSnippets] = this.snippetBound;
                this.possibleSnippets = [];
            });
            event.target.focus();
        },

        updatePossibleSnippets(event) {
            if (
                event.key === 'Tab' ||
                event.keyIdentifier === 'Tab' ||
                event.keyCode === 9 ||
                event.key === 'Shift' ||
                event.keyIdentifier === 'Shift' ||
                event.keyCode === 16 ||
                event.key === 'Alt' ||
                event.keyIdentifier === 'Alt' ||
                event.keyCode === 18 ||
                event.key === 'Escape' ||
                event.keyIdentifier === 'Escape' ||
                event.keyCode === 27 ||
                event.key === 'Control' ||
                event.keyIdentifier === 'Control' ||
                event.keyCode === 17
            ) {
                return;
            }
            if (
                event.key !== 'Delete' &&
                event.keyIdentifier !== 'Delete' &&
                event.keyCode !== 46
            ) {
                this.selectedSnippet = null;
            }

            if (!this.loadedSnippets || !this.valueCopy) {
                this.possibleSnippets = [];
                return;
            }
            this.getPossibleSnippets();
        },

        getPossibleSnippets(force = false) {
            const [start, end] = this.snippetBound;
            this.snippetIndexSelected = null;
            if (start === this.ignoreSnippets || (!force && end - start < 3)) {
                this.possibleSnippets = [];
                return;
            }
            const word = this.valueCopy.slice(start, end) || '';
            this.possibleSnippets = this.findSnippetsByPrefix(word);
        },

        findSnippetsByPrefix(word) {
            return [
                ...(this.assignment ? this.assignment.course.snippets : [])
                    .filter(snip => snip.key.startsWith(word))
                    .sort((a, b) => a.key.localeCompare(b.key))
                    .map(snip => Object.assign({}, snip, { course: true })),
                ...this.findUserSnippetsByPrefix(word),
            ];
        },

        emitInut() {
            this.$emit('input', this.valueCopy);
        },

        onCtrlEnter() {
            this.$emit('ctrlEnter');
        },

        async focusInput() {
            const el = this.$refs.field;
            if (el != null) {
                el.focus();
                // Put the cursor at the end of the text (Safari puts it at the
                // start for some reason...
                await this.$afterRerender();
                el.setSelectionRange(el.value.length, el.value.length);
            }
        },

        doSubmit() {
            if (this.valueCopy === '' || this.valueCopy == null) {
                this.$refs.deleteButton.onClick();
            } else {
                this.$refs.submitButton.onClick();
            }
        },

        async onClickSnippet(i) {
            this.snippetIndexSelected = i;
            const [start] = this.snippetBound;
            await this.$nextTick();
            const selected = this.selectedSnippet;
            const wantedCursor = start + selected.value.length;
            this.confirmSnippet();

            await this.$nextTick();
            const el = this.$refs.field;
            if (el) {
                el.focus();
                el.setSelectionRange(wantedCursor, wantedCursor);
            }
        },

        confirmSnippet() {
            this.snippetIndexSelected = null;
            this.selectedSnippet = null;
            this.getPossibleSnippets();
        },

        maybeSelectNextSnippet(reverse) {
            this.ignoreSnippets = null;

            const { selectionStart, selectionEnd } = this.$refs.field;

            if (selectionStart !== selectionEnd) {
                return;
            }

            const len = this.possibleSnippets.length;
            if (!len) {
                this.getPossibleSnippets(true);
                return;
            }

            if (this.snippetIndexSelected === null) {
                this.snippetIndexSelected = reverse ? len - 1 : 0;
            } else if (reverse && this.snippetIndexSelected === 0) {
                this.snippetIndexSelected = null;
            } else if (reverse) {
                this.snippetIndexSelected -= 1;
            } else if (this.snippetIndexSelected + 1 < len) {
                this.snippetIndexSelected += 1;
            } else {
                this.snippetIndexSelected = null;
            }
        },
    },

    components: {
        Icon,
    },
};
</script>

<style lang="less">
@import '~mixins.less';

.snippet-list-wrapper {
    .default-text-colors;
    position: absolute;
    width: 100%;
    top: 100%;
    z-index: 2;
    margin: 0;

    &.snippets-above {
        position: absolute;
        top: -10.3em;
        height: 10.3em;
        border-bottom-left-radius: 0;
        border-bottom-right-radius: 0;
        box-shadow: 0.2em -0.1em 0.5em 0 rgb(206, 212, 218);

        @{dark-mode} {
            box-shadow: 0.2em -0.1em 0.5em 0 @color-primary;
        }

        .snippet-header {
            height: 2em;
        }

        ~ .form-control {
            border-top-left-radius: 0;
        }
    }
    &:not(.snippets-above) {
        box-shadow: 0.2em 0.1em 0.5em 0 rgb(206, 212, 218);

        @{dark-mode} {
            box-shadow: 0.2em 0.1em 0.5em 0 @color-primary;
        }

        border-top-left-radius: 0;
        border-top-right-radius: 0;
        border-top: 0;

        ~ .form-control {
            border-bottom-left-radius: 0;
        }
    }

    .card-header {
        padding: 5px 15px;
        max-height: 2.3em;
    }
    .card-body {
        padding: 0;
        height: 100%;
    }
}

textarea {
    .default-text-colors;

    font-size: 1em;
}

.snippet-list {
    margin: 0;
    max-height: 8em;
    padding: 0px;
    overflow-y: auto;

    .snippet-list-wrapper:not(.snippets-above) & {
        border-bottom-left-radius: @border-radius;
        border-bottom-right-radius: @border-radius;
    }
    &.inline {
        height: 8em;
    }

    .snippet-item {
        background: white;

        @{dark-mode} {
            background: @color-primary;
            color: white;
        }

        padding: 5px 15px;
        width: 100%;
        list-style: none;
        border-bottom: 1px solid rgba(0, 0, 0, 0.125);

        &:hover,
        &.selected {
            color: white;
        }
        &.selected {
            background: @color-secondary !important;
        }
        &:hover {
            background: lighten(@color-secondary, 20%) !important;
        }
        .snippet-list-wrapper.snippets-above &:first-child {
            border-top: 0;
        }
        .snippet-list-wrapper:not(.snippets-above) &:last-child {
            border-bottom: 0;
            padding-bottom: 5px;
        }
    }
}

</style>
