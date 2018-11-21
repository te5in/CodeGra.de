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
    <div class="feedback-area edit" v-else
         @click.stop>
        <b-collapse class="collapsep"
                    v-if="canUseSnippets"
                    v-model="showSnippetDialog"
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
                                       @click="addSnippet"
                                       v-b-popover.hover.top="'Save snippet'">
                            <icon :scale="1" name="check"/>
                        </submit-button>
                    </b-input-group-append>
                </b-input-group>
            </div>
        </b-collapse>

        <b-input-group class="editable-area">
            <textarea ref="field"
                      v-model="internalFeedback"
                      class="form-control"
                      style="font-size: 1em;"
                      @keydown.tab="expandSnippet"
                      @keydown.ctrl.enter.prevent="submitFeedback"
                      @keydown.esc="revertFeedback"/>
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
    },

    data() {
        return {
            internalFeedback: this.feedback,
            serverFeedback: this.feedback,
            done: true,
            snippetKey: '',
            showSnippetDialog: false,
        };
    },

    async mounted() {
        if (this.editing) {
            await this.maybeRefreshSnippets();
        }

        this.$nextTick(() => {
            if (!this.done || this.editing) {
                this.$refs.field.focus();
            }
        });
    },

    watch: {
        editing() {
            this.maybeRefreshSnippets();
        },
    },

    computed: {
        ...mapGetters({
            snippets: 'user/snippets',
            nameCurrentUser: 'user/name',
        }),
    },

    methods: {
        ...mapActions({
            maybeRefreshSnippets: 'user/maybeRefreshSnippets',
            addSnippetToStore: 'user/addSnippet',
            updateSnippetInStore: 'user/updateSnippet',
        }),

        changeFeedback(e) {
            if (this.editable) {
                this.done = false;
                this.$nextTick(() => this.$refs.field.focus());
                this.internalFeedback = this.serverFeedback;
                e.stopPropagation();
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

        revertFeedback() {
            if (this.serverFeedback === '') {
                this.cancelFeedback(false);
            } else {
                this.$emit('feedbackChange', {
                    line: this.line,
                    msg: this.serverFeedback,
                }, true);
                this.done = true;
            }
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

        expandSnippet(event) {
            event.preventDefault();

            if (!this.canUseSnippets) {
                return;
            }

            const { selectionStart, selectionEnd } = this.$refs.field;

            if (selectionStart !== selectionEnd) {
                return;
            }

            const val = this.internalFeedback.slice(0, selectionEnd);
            const start = Math.max(val.lastIndexOf(' '), val.lastIndexOf('\n')) + 1;
            const key = val.slice(start, selectionEnd);

            if (key in this.snippets) {
                const { value } = this.snippets[key];
                this.internalFeedback = val.slice(0, start) + value +
                    this.internalFeedback.slice(selectionEnd);
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
    z-index: 1000;
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
</style>

<style lang="less">
.feedback-area .minor-buttons .submit-button.btn:last-child {
    border-bottom-right-radius: 0px;
    border-bottom-left-radius: 0px;
    border-top-right-radius: 0px;
    border-top-left-radius: 0px;
}
</style>
