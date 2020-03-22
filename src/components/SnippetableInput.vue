<template>
<b-input-group
    class="editable-area"
    :style="{ 'margin-bottom': notSnippetsAbsoluteBelow && !showSnippetsAbove ?
            '11em' :
            undefined }">
    <div style="flex: 1; position: relative;">
        <b-card class="snippet-list-wrapper"
                :class="{ 'snippets-above': showSnippetsAbove }"
                v-if="possibleSnippets.length > 0">
            <span slot="header"
                  class="snippet-header">Snippets (press <kbd>Tab</kbd> to select the next item)</span>
            <ul :class="{ 'snippet-list': true, inline: line + 6 >= totalAmountLines, }">
                <li class="snippet-item"
                    v-for="snippet, i in possibleSnippets"
                    :class="{ selected: snippetIndexSelected === i }"
                    ref="snippets"
                    :key="`snippet-key:${snippet.key}:${snippet.course}`"
                    @click="snippetIndexSelected = i">
                    <span v-if="snippet.course" class="snippet-icon"><icon :scale="0.9" name="book"/></span>
                    <span v-else class="snippet-icon"><icon :scale="0.9" name="user-circle-o"/></span>
                    <span>{{ snippet.key }}</span>
                    <span>- {{ snippet.value }}</span>
                </li>
            </ul>
        </b-card>
        <textarea ref="field"
                  v-model="valueCopy"
                  class="form-control editable-feedback-area rounded-right-0"
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
    },

    data() {
        return {
            possibleSnippets: [],
            valueCopy: this.value,
            ignoreSnippets: null,
            emitTimer: null,
        };
    },

    watch: {
        valueCopy() {
            this.emitLater();
        },

        value() {
            this.valueCopy = this.value;
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
            const { selectionEnd } = this.$refs.field;

            const spaceIndex = lastWhiteSpace(this.valueCopy, selectionEnd) + 1;
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
            if (!this.editing || !this.loadedSnippets || !this.valueCopy) {
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

        maybeClearEmitTimeout() {
            if (this.emitTimer != null) {
                clearTimeout(this.emitTimer);
            }
        },

        emitLater() {
            this.maybeClearEmitTimeout();
            this.emitTimer = setTimeout(() => {
                this.$emit('input', this.valueCopy);
                this.emitTimer = null;
            }, this.bounceTime);
        },

        emitNow() {
            this.maybeClearEmitTimeout();
            this.$emit('input', this.valueCopy);
        },

        onCtrlEnter() {
            this.emitNow();
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

        confirmSnippet() {
            this.snippetIndexSelected = null;
            this.selectedSnippet = null;
            this.getPossibleSnippets();
        },

        maybeSelectNextSnippet(reverse) {
            if (!this.canUseSnippets) {
                return;
            }
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
};
</script>
