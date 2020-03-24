<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="feedback-reply">
    <b-card no-body v-if="editing">
        <b-tabs card>
            <b-tab title="Edit" active>
                <b-collapse class="collapsep"
                            v-model="showSnippetDialog"
                            v-if="canUseSnippets"
                            :id="`collapse${line}`"
                            style="margin: 0">
                    <div>
                        <b-input-group class="input-snippet-group mb-2">
                            <input class="input form-control"
                                   v-model="snippetKey"
                                   :disabled="inputDisabled"
                                   @keydown.ctrl.enter="() => addSnippetButton.onClick()"/>
                            <b-input-group-append>
                                <submit-button ref="addSnippetButton"
                                               class="add-snippet-btn"
                                               :submit="addSnippet"
                                               :confirm="addSnippetConfirm"
                                               @after-success="afterAddSnippet"
                                               @error="inputDisabled = false">
                                    <icon :scale="1" name="check"/>
                                </submit-button>
                            </b-input-group-append>
                        </b-input-group>
                    </div>
                </b-collapse>

                <div>
                    <snippetable-input
                        :value="internalReply.message"
                        @input="onInput"
                        :min-initial-height="100"
                        :force-snippets-above="forceSnippetsAbove"
                        :total-amount-lines="totalAmountLines"
                        :feedback-disabled="inputDisabled"
                        :can-use-snippets="canUseSnippets"
                        :line="feedbackLine.line"
                        ref="inputField"
                        @ctrlEnter="doSubmit"
                        :bounce-time="300" />

                    <div class="save-button-wrapper mt-2">
                        <submit-button
                            ref="deleteButton"
                            variant="danger"
                            :submit="deleteFeedback"
                            @error="inputDisabled = false"
                            @success="onDeleteFeedback"
                            :confirm="(reply.isEmpty && internalReply.isEmpty) ?  '' : 'Are you sure you want to delete this comment?'"
                            @after-success="afterDeleteFeedback"
                            label="Delete" />

                        <b-btn @click="cancelEditing"
                               variant="primary">
                            Cancel
                        </b-btn>

                        <submit-button :submit="submitFeedback"
                                       @after-success="afterSubmitFeedback"
                                       :disabled="internalReply.isEmpty"
                                       @error="inputDisabled = false"
                                       ref="submitButton"
                                       label="Save"  />
                    </div>
                </div>
            </b-tab>
            <b-tab title="Preview"
               lazy
               :disabled="internalReply.replyType !== 'markdown' || internalReply.isEmpty">
            <div class="p-2">
                <inner-markdown-viewer
                    :markdown="internalReply.message"
                    class="markdown-message" />
            </div>
        </b-tab>
    </b-tabs>
    </b-card>

    <template v-else>
        <div class="d-flex justify-content-between">
            <div>
                <user :user="reply.author" :show-you="true" />
                <span class="text-muted">{{ reply.createdAt.from($root.$now) }}</span>
            </div>
            <div>
                <b-dropdown toggle-class="feedback-reply-settings-toggle p-0 border-0 bg-transparent"
                            dropup
                            @hide="onDropDownHide">
                    <template v-slot:button-content>
                        <icon class="cursor-pointer" name="gear" :id="gearId"/>
                    </template>

                    <li>
                        <submit-button
                            class="dropdown-item rounded-0"
                            ref="deleteButton"
                            variant="secondary"
                            :submit="deleteFeedback"
                            @error="inputDisabled = false"
                            @success="onDeleteFeedback"
                            @after-success="afterDeleteFeedback"
                            label="Delete" />
                    </li>
                    <b-dropdown-item
                        href="#"
                        @click="startEdit">
                        Edit
                    </b-dropdown-item>
                </b-dropdown>
            </div>
        </div>
        <b-card :style="{'min-height': '1em'}"
                class="feedback-reply-message p-2">

            <div v-html="newlines($utils.htmlEscape(internalReply.message))"
                 class="plain-text-message"
                 v-if="internalReply.replyType === 'plain_text'"  />
            <inner-markdown-viewer
                :markdown="internalReply.message"
                class="markdown-message"
                v-else />

        </b-card>
    </template>
</div>
</template>

<script lang="ts">
    import { Vue, Component, Prop, Ref, Watch } from 'vue-property-decorator';

// @ts-ignore
import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/check';
import 'vue-awesome/icons/times';
import 'vue-awesome/icons/plus';
import 'vue-awesome/icons/gear';

import { mapActions, mapGetters } from 'vuex';

// @ts-ignore
import { Submission } from '@/models/submission';

import { FeedbackReply as FeedbackReplyModel, FeedbackLine, Assignment, User as UserModel } from '@/models';
// @ts-ignore
import User from './User';
// @ts-ignore
import SubmitButton from './SubmitButton';
// @ts-ignore
import InnerMarkdownViewer from './InnerMarkdownViewer';
// @ts-ignore
import SnippetableInput from './SnippetableInput';

@Component({
    computed: {
        ...mapGetters({
            snippets: 'user/snippets',
        }),

    },
    methods: {
        ...mapActions('user', {
            addSnippetToStore: 'addSnippet',
            updateSnippetInStore: 'updateSnippet',
        }),
    },
    components: {
        Icon,
        SubmitButton,
        SnippetableInput,
        InnerMarkdownViewer,
        User,
    },
})

export default class FeedbackReply extends Vue {
    snippets!: Record<string, any>;

    addSnippetToStore!: any;

    updateSnippetInStore!: any;

    // @ts-ignore
    @Prop({ required: true }) reply: FeedbackReplyModel

    @Prop({ required: true }) feedbackLine!: FeedbackLine

    @Prop({ default: false }) editable!: boolean

    @Prop({ default: false }) forceSnippetsAbove!: boolean

    @Prop({ required: true }) totalAmountLines!: number

    @Prop({ required: true }) submission!: Submission

    @Prop({ required: true }) canUseSnippets!: boolean

    get assignment(): Assignment {
        return this.submission.assignment;
    }

    internalReply: FeedbackReplyModel = this.reply;

    @Watch('reply')
    onReplyUpdate() {
        this.internalReply = this.reply;
    }

    snippetKey: string = '';

    snippetDisabled: boolean = false;

    showSnippetDialog: boolean = false

    inputDisabled: boolean = false;

    wasClicked: boolean = false;

    startEdit() {
        this.wasClicked = true;
    }

    get editing(): boolean {
        return this.editable && (this.reply.id == null || this.wasClicked);
    }

    @Watch('editing', { immediate: true })
    onEditingChange(): void {
        if (this.editing) {
            this.focusInput();
        }
    }

    get line(): number {
        return this.feedbackLine.line;
    }

    get author(): UserModel | null {
        return this.reply.author;
    }

    get addSnippetConfirm() {
        if (this.snippetKey in this.snippets) {
            return `There is already a snippet with key "${this.snippetKey}".
Do you want to overwrite it?`;
        } else {
            return '';
        }
    }

    get gearId(): string {
        return `feedback-edit-gear-${this.reply.trackingId}`;
    }

    @Ref() readonly inputField: SnippetableInput | null

    @Ref() readonly submitButton: SubmitButton | null

    @Ref() readonly deleteButton: SubmitButton | null

    @Ref() readonly addSnippetButton: SubmitButton | null;

    onInput(event: string) {
        this.internalReply = this.internalReply.update(event);
    }

    async focusInput(): Promise<void> {
        await this.$nextTick();

        const el = this.inputField;
        if (el != null) {
            el.focus();
        }
    }

    cancelEditing(): void {
        this.internalReply = this.reply;
        if (this.reply.isEmpty) {
            this.afterDeleteFeedback();
        }
        this.inputDisabled = false;
        this.wasClicked = false;
    }

    submitFeedback(): Promise<object> {
        if (this.internalReply.isEmpty) {
            return this.deleteFeedback();
        }

        this.inputDisabled = true;

        return this.internalReply.save();
    }

    afterSubmitFeedback(response: any): void {
        this.$emit('updated', this.internalReply.updateFromServerData(response.data));
        this.inputDisabled = false;
        this.wasClicked = false;
    }

    afterDeleteFeedback(): void {
        this.$emit('deleted', this.internalReply);
    }

    onDeleteFeedback(): void {
        if (this.internalReply.id == null) {
            this.afterDeleteFeedback();
        }
    }

    doSubmit() {
        if (this.internalReply.isEmpty) {
            this.deleteButton.onClick();
        } else {
            this.submitButton.onClick();
        }
    }

    submitFeedabckError() {
        this.inputDisabled = false;
    }

    // eslint-disable-next-line
    newlines(value: string): string {
        return value.replace(/\n/g, '<br>');
    }

    deleteFeedback(): Promise<object> {
        this.inputDisabled = true;
        this.snippetKey = '';
        return this.internalReply.delete();
    }

    onDropDownHide(bvEvent: any): void {
        if (this.deleteButton.state !== 'default') {
            bvEvent.preventDefault();
        }
    }

    // eslint-disable-next-line
    deleteFilter<T extends Record<string, Record<string, number>>>(err: T): T {
        if (err.response && err.response.status === 404) {
            return err;
        } else {
            throw err;
        }
    }

    deleteFeedbackError() {
        this.inputDisabled = false;
    }

    addSnippet() {
        const key = this.snippetKey;
        const value = this.internalReply.message;

        if (key.match(/\s/)) {
            throw new Error('No spaces allowed!');
        } else if (!key) {
            throw new Error('Snippet key cannot be empty');
        } else if (!value) {
            throw new Error('Snippet value cannot be empty');
        }

        this.inputDisabled = true;

        if (key in this.snippets) {
            const { id } = this.snippets[key];
            return this.$http.patch(`/api/v1/snippets/${id}`, { key, value }).then(() => {
                this.updateSnippetInStore({ id, key, value });
            });
        } else {
            return this.$http
                .put('/api/v1/snippet', { key, value })
                .then(({ data: newSnippet }) => {
                    this.addSnippetToStore(newSnippet);
                });
        }
    }

    afterAddSnippet() {
        this.inputDisabled = false;

        this.$root.$emit('bv::toggle::collapse', `collapse${this.line}`);
    }

    findSnippet() {
        if (this.snippetKey !== '' || this.showSnippetDialog) {
            return;
        }

        const keys = Object.keys(this.snippets);
        for (let i = 0, len = keys.length; i < len; i += 1) {
            if (this.internalReply.message === this.snippets[keys[i]].value) {
                this.snippetKey = keys[i];
                return;
            }
        }
    }
}
</script>

<style lang="less" scoped>
@import '~mixins.less';

.feedback-reply {
    .default-text-colors;
    background-color: white;

    @{dark-mode} {
        background-color: @color-primary-darker;
    }

    display: flex;
    align-items: top;

    @media @media-small {
        flex-direction: column-reverse;
    }

    font-size: 1.1em;

    .feedback-reply-message {
        margin-top: 0;

        @{dark-mode} {
            background-color: @color-primary;
            border-color: @color-primary-darkest;
            color: @text-color-dark;
        }

        .plain-text-message {
            white-space: pre-wrap;
            word-break: break-word;
        }

    }

    &.edit {
        position: relative;
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
    button,
    .submit-button {
        flex: 1;
        &:first-child {
            border-top-right-radius: 0;
            border-top-left-radius: 0;
        }
    }
    min-height: 7em;
}

.collapsep {
    float: right;
    display: flex;
}

.snippet-btn {
    border-top-width: 1px;
    border-top-style: solid;
}

.snippet-btn .fa-icon {
    transform: translateY(-1px) rotate(0);
    transition: transform @transition-duration;

    &.rotated {
        transform: translateY(-1px) rotate(45deg);
    }
}

.input.snippet {
    margin: 0;
}

.input-snippet-group {
    padding-top: 0;
}

.editable-feedback-reply {
    position: relative;
    min-height: 7em;
    font-size: 1em;
}

.snippet-icon {
    display: inline-block;
    width: 1rem;

    .fa-icon {
        vertical-align: middle;
        margin-top: -3px;
    }
}

.save-button-wrapper {
    text-align: right;
}
</style>

<style lang="less">
@import '~mixins.less';

.feedback-reply .user .group-user,
.feedback-reply .user .name-user {
    font-weight: bold;
}

.feedback-reply .feedback-reply-settings-toggle {
}

.feedback-reply .markdown-message {
    & > *:first-child {
        margin-top: 0;
    }

    & > *:last-child {
        margin-bottom: 0;
    }

    p {
        margin-bottom: 0.5em;
    }

    pre.code-block {
        margin-left: 0;
        padding: 1.5rem;
        border-radius: @border-radius;
        background: @color-lightest-gray;
    }
}

.snippetable-input {
    font-family: monospace;
}
</style>
