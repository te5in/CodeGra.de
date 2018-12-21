<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="feedback-area-wrapper non-editable" v-if="(done && !editing)">
    <div class="author" v-if="author">{{ author }}</div>
    <b-card class="feedback-area non-editable" :class="{'has-author': author != null}">
        <div @click="changeFeedback($event)" :style="{'min-height': '1em'}">
            <div v-html="newlines($htmlEscape(serverFeedback))"></div>
        </div>
    </b-card>
</div>
<div class="feedback-area edit" v-else @click.stop>
    <b-collapse class="collapsep"
                v-model="showSnippetDialog"
                v-if="canUseSnippets"
                :id="`collapse${line}`"
                style="margin: 0">
        <div>
            <b-input-group class="input-snippet-group">
                <input class="input form-control"
                       v-model="snippetKey"
                       @keydown.ctrl.enter="addSnippet"/>
                <b-input-group-append>
                    <submit-button ref="addSnippetButton"
                                   class="add-snippet-btn"
                                   label=""
                                   @click="addSnippet">
                        <icon :scale="1" name="check"/>
                    </submit-button>
                </b-input-group-append>
            </b-input-group>
        </div>
    </b-collapse>

    <b-input-group
        class="editable-area"
        :style="{ 'margin-bottom': possibleSnippets.length && line + 6 >= totalAmountLines ?
                '11em' :
                undefined }">
        <div style="flex: 1; position: relative;">
            <b-card class="snippet-list-wrapper"
                    v-if="possibleSnippets.length > 0">
                <span slot="header">Snippets (press <kbd>Tab</kbd> to select the next item)</span>
                <ul
                    :class="{ 'snippet-list': true, inline: line + 6 >= totalAmountLines, }">
                    <li class="snippet-item"
                        v-for="snippet, i in possibleSnippets"
                        :class="{ selected: snippetSelected === i }"
                        ref="snippets"
                        :key="`snippet-key:${snippet.key}`"
                        @click="snippetSelected = i">
                        {{ snippet.key }} - {{ snippet.value }}
                    </li>
                </ul>
            </b-card>
            <textarea ref="field"
                      v-model="internalFeedback"
                      class="form-control editable-feedback-area"
                      @keydown.esc.prevent="stopSnippets"
                      @keydown.exact.tab.prevent="maybeSelectNextSnippet(false)"
                      @keydown.exact.shift.tab.prevent="maybeSelectNextSnippet(true)"
                      @keydown="beforeKeyPress"
                      @keyup="updatePossibleSnippets"
                      @keydown.ctrl.enter.prevent="submitFeedback"/>
        </div>
        <div class="minor-buttons btn-group-vertical">
                <b-btn class="snippet-btn"
                       variant="secondary"
                       v-if="canUseSnippets"
                       @click="findSnippet(); showSnippetDialog = !showSnippetDialog"
                       v-b-popover.top.hover="showSnippetDialog ? 'Hide snippet name' : 'Save as snippet'">
                    <icon name="plus"
                          aria-hidden="true"
                          :class="{ rotated: showSnippetDialog }"/>
                </b-btn>
                <submit-button @click="cancelFeedback"
                               ref="deleteFeedbackButton"
                               default="danger"
                               :label="false"
                               v-b-popover.top.hover="'Delete feedback'">
                    <icon name="times" aria-hidden="true"/>
                </submit-button>
            </div>
            <b-input-group-append class="submit-feedback">
                <submit-button @click="submitFeedback"
                               ref="addFeedbackButton"
                               :label="false"
                               v-b-popover.top.hover="'Save feedback'">
                    <icon name="check" aria-hidden="true"/>
                </submit-button>
            </b-input-group-append>
        </b-input-group>
    </div>
</template>

<script>
import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/refresh';
import 'vue-awesome/icons/check';
import 'vue-awesome/icons/times';
import 'vue-awesome/icons/plus';

import { mapActions, mapGetters } from 'vuex';

import { waitAtLeast } from '@/utils';
import SubmitButton from './SubmitButton';

export default {
    name: 'feedback-area',

    props: {
        line: {
            type: Number,
            required: true,
        },

        feedback: {
            type: String,
            required: true,
        },

        author: {
            type: [String, Object],
            required: false,
            default: undefined,
        },

        fileId: {
            type: Number,
            required: true,
        },

        editable: {
            type: Boolean,
            default: false,
        },

        editing: {
            type: Boolean,
            default: false,
        },

        canUseSnippets: {
            type: Boolean,
            default: false,
        },

        totalAmountLines: {
            type: Number,
            required: true,
        },
    },

    data() {
        return {
            internalFeedback: this.feedback,
            serverFeedback: this.feedback,
            done: false,
            snippetKey: '',
            loadedSnippets: null,
            snippetSelected: null,
            snippetKeySelected: null,
            snippetOldKey: null,
            possibleSnippets: [],
            ignoreSnippets: null,
            showSnippetDialog: false,
        };
    },

    async mounted() {
        if (this.editing) {
            this.loadedSnippets = false;
            await this.maybeRefreshSnippets();
            this.loadedSnippets = true;
        }

        this.$nextTick(() => {
            if (this.editing) {
                this.$refs.field.focus();
            }
        });
    },

    watch: {
        async editing() {
            this.loadedSnippets = false;
            await this.maybeRefreshSnippets();
            this.loadedSnippets = true;
        },

        snippetSelected(_, oldVal) {
            // eslint-disable-next-line
            let [start, end] = this.snippetBound;
            let value;

            if (this.snippetSelected === null) {
                if (this.snippetKeySelected === null) {
                    return;
                }
                this.snippetKeySelected = null;
                value = this.snippetOldKey;
                const oldSnip = this.possibleSnippets[oldVal];
                if (oldSnip != null) {
                    start = end - oldSnip.value.length;
                }
                const el = this.$refs.snippets[oldVal === 0 ? this.$refs.snippets.length - 1 : 0];
                if (el && el.scrollIntoView) {
                    el.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'smooth' });
                }
            } else {
                const newSnip = this.possibleSnippets[this.snippetSelected];
                if (!newSnip || newSnip.key === this.snippetKeySelected) {
                    return;
                }

                [1, 0].forEach((i) => {
                    const el = this.$refs.snippets[this.snippetSelected + i];
                    if (el && el.scrollIntoView) {
                        el.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'smooth' });
                    }
                });

                this.snippetKeySelected = newSnip.key;
                if (oldVal === null) {
                    this.snippetOldKey = this.internalFeedback.slice(start, end) || '';
                } else {
                    const oldSnip = this.possibleSnippets[oldVal];
                    start = end - oldSnip.value.length;
                }
                ({ value } = newSnip);
            }
            this.internalFeedback = this.internalFeedback.slice(0, start) + value +
                this.internalFeedback.slice(end);
        },
    },

    computed: {
        ...mapGetters({
            snippets: 'user/snippets',
            nameCurrentUser: 'user/name',
            findSnippetsByPrefix: 'user/findSnippetsByPrefix',
        }),

        snippetBound() {
            if (this.done || !this.internalFeedback) {
                return [0, 0];
            }
            const { selectionEnd } = this.$refs.field;

            const spaceIndex = this.lastWhiteSpace(this.internalFeedback, selectionEnd) + 1;
            if (this.ignoreSnippets != null && this.ignoreSnippets !== spaceIndex) {
                this.ignoreSnippets = null;
            }
            return [spaceIndex, selectionEnd];
        },
    },

    methods: {
        ...mapActions({
            maybeRefreshSnippets: 'user/maybeRefreshSnippets',
            addSnippetToStore: 'user/addSnippet',
            updateSnippetInStore: 'user/updateSnippet',
        }),

        lastWhiteSpace(str, start) {
            let i = start;
            for (; i > -1; i--) {
                const val = str[i];
                if (val === ' ' || val === '\n' || val === '\t') {
                    return i;
                }
            }
            return -1;
        },

        beforeKeyPress(event) {
            if ((event.key === 'Backspace' || event.keyIdentifier === 'Backspace' || event.keyCode === 8) &&
                (event.selectionStart !== event.selectionEnd || this.snippetSelected !== null)) {
                event.preventDefault();
                this.snippetSelected = null;
            } else if ((event.key === 'Enter' || event.keyIdentifier === 'Enter' || event.keyCode === 13) &&
                       this.snippetSelected !== null) {
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
            this.snippetSelected = null;
            this.$nextTick().then(() => {
                [this.ignoreSnippets] = this.snippetBound;
                this.possibleSnippets = [];
            });
            event.target.focus();
        },

        updatePossibleSnippets(event) {
            if (event.key === 'Tab' || event.keyIdentifier === 'Tab' || event.keyCode === 9 ||
                event.key === 'Shift' || event.keyIdentifier === 'Shift' || event.keyCode === 16 ||
                event.key === 'Alt' || event.keyIdentifier === 'Alt' || event.keyCode === 18 ||
                event.key === 'Escape' || event.keyIdentifier === 'Escape' || event.keyCode === 27 ||
                event.key === 'Control' || event.keyIdentifier === 'Control' || event.keyCode === 17) {
                return;
            }
            if (event.key !== 'Delete' && event.keyIdentifier !== 'Delete' && event.keyCode !== 46) {
                this.snippetKeySelected = null;
            }
            if (this.done ||
                !this.loadedSnippets ||
                !this.internalFeedback) {
                this.possibleSnippets = [];
                return;
            }
            this.getPossibleSnippets();
        },

        getPossibleSnippets(force = false) {
            const [start, end] = this.snippetBound;
            this.snippetSelected = null;
            if (start === this.ignoreSnippets || (!force && end - start < 3)) {
                this.possibleSnippets = [];
                return;
            }
            const word = this.internalFeedback.slice(start, end) || '';
            this.possibleSnippets = this.findSnippetsByPrefix(word);
        },


        async changeFeedback(e) {
            if (this.editable) {
                this.done = false;
                this.$nextTick(() => this.$refs.field.focus());
                this.internalFeedback = this.serverFeedback;
                e.stopPropagation();
                this.loadedSnippets = false;
                await this.maybeRefreshSnippets();
                this.loadedSnippets = true;
            }
        },

        focusInput() {
            this.$nextTick(() => {
                if (this.$refs.field) this.$refs.field.focus();
            });
        },

        submitFeedback() {
            if (this.internalFeedback === '' || this.internalFeedback == null) {
                this.cancelFeedback();
                return;
            }

            const submitted = this.internalFeedback;

            const req = this.$http.put(
                `/api/v1/code/${this.fileId}/comments/${this.line}`,
                {
                    comment: submitted,
                },
            ).then(() => {
                this.internalFeedback = submitted;
                this.serverFeedback = submitted;
                this.snippetKey = '';
                this.done = true;
                this.$emit('feedbackChange', {
                    line: this.line,
                    msg: submitted,
                    author: { name: this.nameCurrentUser },
                });
            }, (err) => {
                throw err.response.data.message;
            });

            this.$refs.addFeedbackButton.submit(req);
        },

        newlines(value) {
            return value.replace(/\n/g, '<br>');
        },

        cancelFeedback() {
            this.snippetKey = '';

            if (this.feedback !== '') {
                const req = this.$http.delete(
                    `/api/v1/code/${this.fileId}/comments/${this.line}`,
                ).then(
                    () => this.$emit('cancel', this.line),
                    (err) => {
                        // Don't error for a 404 as the comment was deleted.
                        if (err.response.status === 404) {
                            this.$emit('cancel', this.line);
                        } else {
                            throw err.response.data.message;
                        }
                    },
                );

                this.$refs.deleteFeedbackButton.submit(req);
            } else {
                this.$emit('cancel', this.line);
            }
        },

        confirmSnippet() {
            this.snippetSelected = null;
            this.snippetKeySelected = null;
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

            if (this.snippetSelected === null) {
                this.snippetSelected = reverse ? len - 1 : 0;
            } else if (reverse && this.snippetSelected === 0) {
                this.snippetSelected = null;
            } else if (reverse) {
                this.snippetSelected -= 1;
            } else if (this.snippetSelected + 1 < len) {
                this.snippetSelected += 1;
            } else {
                this.snippetSelected = null;
            }
        },

        addSnippet() {
            const key = this.snippetKey;
            const value = this.internalFeedback;

            if (key.match(/\s/)) {
                this.$refs.addSnippetButton.fail('No spaces allowed!');
                return null;
            } else if (!key) {
                this.$refs.addSnippetButton.fail('Snippet key cannot be empty');
                return null;
            } else if (!value) {
                this.$refs.addSnippetButton.fail('Snippet value cannot be empty');
                return null;
            }

            let req;
            if (key in this.snippets) {
                const { id } = this.snippets[key];
                req = this.$http.patch(`/api/v1/snippets/${id}`, { key, value }).then(
                    () => { this.updateSnippetInStore({ id, key, value }); },
                );
            } else {
                req = this.$http.put('/api/v1/snippet', { key, value }).then(
                    ({ data: newSnippet }) => {
                        this.addSnippetToStore(newSnippet);
                    },
                );
            }

            return this.$refs.addSnippetButton.submit(
                waitAtLeast(500, req.catch((err) => { throw err.response.data.message; })),
            ).then((success) => {
                if (success) {
                    this.$root.$emit('collapse::toggle', `collapse${this.line}`);
                }
            });
        },

        findSnippet() {
            if (this.snippetKey !== '' || this.showSnippetDialog) {
                return;
            }

            const keys = Object.keys(this.snippets);
            for (let i = 0, len = keys.length; i < len; i += 1) {
                if (this.internalFeedback === this.snippets[keys[i]].value) {
                    this.snippetKey = keys[i];
                    return;
                }
            }
        },
    },

    components: {
        Icon,
        SubmitButton,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.snippet-list-wrapper {
    position: absolute;
    width: 100%;
    top: 100%;
    z-index: 10;
    margin: 0;
    .card-header {
        padding: 5px 15px;
    }
    .card-body {
        padding: 0;
        height: 100%;
    }

    ~ .form-control {
        box-shadow: none;
        transition: box-shadow 0.2s ease-in;
        border-bottom-left-radius: 0;
    }
    border-top-left-radius: 0;
    border-top-right-radius: 0;
    border-top: 0;
}

.snippet-list {
    margin: 0;
    max-height: 8em;
    padding: 0px;
    overflow-y: auto;
    border-bottom-left-radius: 0.25rem;
    &.inline {
        height: 8em;
    }

    .snippet-item {
        background: white;
        #app.dark & {
            background: @color-primary;
            color: white;
        }

        padding: 5px 15px;
        width: 100%;
        list-style: none;
        border-bottom: 1px solid rgba(0, 0, 0, 0.125);

        &:hover, &.selected {
            color: white;
        }
        &.selected {
            background: @color-secondary !important;
        }
        &:hover {
            background: lighten(@color-secondary, 20%) !important;
        }
        &:last-child {
            border-bottom: 0;
            padding-bottom: 5px;
        }
    }
}

.author {
    flex: 0 1 auto;
    padding: 0.5rem 10px;
    max-width: 20%;
    overflow: hidden;
    text-overflow: ellipsis;
}

.feedback-area-wrapper {
    .default-text-colors;
    background-color: white;

    #app.dark & {
        background-color: @color-primary-darker;
    }

    &.non-editable {
        display: flex;
        align-items: top;
        border: 1px solid rgba(0, 0, 0, 0.125);
        border-radius: 0.25rem;
    }
}

.feedback-area {
    &.non-editable {
        margin-top: 0;
        background-color: @footer-color;
        flex: 1 1 auto;
        &.has-author {
            border-top: 0;
            border-right: 0;
            border-bottom: 0;
            border-top-left-radius: 0;
            border-bottom-left-radius: 0;
        }
        &:not(.has-author) {
            border: 0;
        }

        #app.dark & {
            background-color: @color-primary;
            border-color: @color-primary-darkest;
        }
        white-space: pre-wrap;
        word-break: break-word;
    }

    &.edit {
        position: relative;
        padding-top: @line-spacing;
    }
}

.card-body {
    padding: 0.5rem;
}

button {
    border: none;
    box-shadow: none !important;
}

.minor-buttons {
    z-index: 1;
    &:hover {
        box-shadow: none;
    }
    button, .submit-button {
        flex: 1;
        &:first-child {
            border-top-right-radius: 0px;
            border-top-left-radius: 0px;
        }
    }
    min-height: 7em;
}

.collapsep {
    float: right;
    display: flex;
}

textarea {
    #app.dark & {
        border: 0;
    }
    min-height: 7em;
}

#app:not(.dark) .snippet-btn {
    border-top-width: 1px;
    border-top-style: solid;
}

.snippet-btn .fa-icon {
    transform: rotate(0);
    transition: transform @transition-duration;

    &.rotated {
        transform: rotate(45deg);
    }
}

.editable-area {
    #app.dark & {
        border: .5px solid @color-secondary;
    }
    padding: 0;
    border-radius: 0.25rem;
}

.input.snippet {
    margin: 0;
}

.input-snippet-group {
    padding-top: 0;
}

.editable-feedback-area {
    font-size: 1em;
    position: relative;
    border-top-right-radius: 0;
    border-bottom-right-radius: 0;
}
</style>

<style lang="less">
.feedback-area .minor-buttons .submit-button.btn:last-child {
    border-bottom-right-radius: 0px;
    border-bottom-left-radius: 0px;
    border-top-right-radius: 0px;
    border-top-left-radius: 0px;
}
</style>
