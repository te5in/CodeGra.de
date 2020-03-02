<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<component :is="inPopover ? 'b-btn' : 'div'"
           :id="btnId"
           class="general-feedback-area"
           v-b-popover.hover.top="inPopover ? 'Edit general feedback' : ''">
    <icon name="edit"/>

    <component :is="inPopover ? 'b-popover' : 'div'"
               :id="popoverId"
               ref="popover"
               triggers="click blur"
               :target="btnId"
               :placement="placement"
               :boundary="boundary"
               :container="container"
               @shown="focusTextarea"
               @hide="maybeSaveFeedback">
        <template slot="title">
            <span v-if="submission && submission.comment_author">
                General feedback by <user :user="submission.comment_author"/>
            </span>
            <span v-else>
                General feedback
            </span>
        </template>

        <div class="clearfix">
            <textarea v-if="editable"
                      ref="textarea"
                      :placeholder="placeholder"
                      class="form-control"
                      :rows="10"
                      v-model="feedback"
                      @keydown.ctrl.enter.prevent="$refs.submitButton.onClick"
                      @keydown.tab.capture="expandSnippet" />
            <pre class="feedback-field"
                 v-else-if="feedback">{{ feedback }}</pre>
            <pre class="feedback-field text-muted"
                 v-else>{{ placeholder }}</pre>

            <submit-button v-if="editable"
                           ref="submitButton"
                           :confirm="confirmMsg"
                           :submit="submitFeedback"
                           @success="afterSubmitFeedback"
                           @after-success="maybeHidePopover"
                           @reject-confirm="maybeHidePopover($event, true)"
                           @click.native.capture="manualSave = true"
                           class="float-right my-2" />
        </div>
    </component>
</component>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';

import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/edit';

import User from './User';
import SubmitButton from './SubmitButton';

export default {
    name: 'general-feedback-area',

    props: {
        editable: {
            type: Boolean,
            default: false,
        },
        assignment: {
            type: Object,
            required: true,
        },
        submission: {
            type: Object,
            required: true,
        },
        inPopover: {
            type: Boolean,
            default: false,
        },
        boundary: {
            type: String,
            default: 'window',
        },
        container: {
            type: String,
            default: null,
        },
        placement: {
            type: String,
            default: 'bottom',
        },
    },

    computed: {
        ...mapGetters('user', {
            nameCurrentUser: 'name',
            userId: 'id',
            snippets: 'snippets',
        }),

        submissionId() {
            return this.$utils.getProps(this.submission, null, 'id');
        },

        feedbackChanged() {
            return this.feedback !== this.submission.comment;
        },

        placeholder() {
            return this.feedback || 'No feedback given :(';
        },
    },

    data() {
        const id = this.$utils.getUniqueId();
        return {
            btnId: `general-feedback-toggle-${id}`,
            popoverId: `general-feedback-popover-${id}`,
            feedback: this.submission.comment,
            confirmMsg: '',
            manualSave: false,
        };
    },

    watch: {
        submissionId() {
            this.reset();
        },
    },

    methods: {
        ...mapActions('user', ['refreshSnippets']),
        ...mapActions('submissions', ['updateSubmission']),

        submitFeedback() {
            const data = { feedback: this.feedback || '' };

            return this.$http.patch(`/api/v1/submissions/${this.submission.id}`, data);
        },

        afterSubmitFeedback() {
            this.updateSubmission({
                assignmentId: this.assignment.id,
                submissionId: this.submission.id,
                submissionProps: {
                    comment: this.feedback || '',
                    comment_author: {
                        id: this.userId,
                    },
                },
            });
        },

        expandSnippet(event) {
            const field = event.target;
            const end = field.selectionEnd;
            if (field.selectionStart === end) {
                event.preventDefault();
                const val = this.feedback.slice(0, end);
                const start = Math.max(val.lastIndexOf(' '), val.lastIndexOf('\n')) + 1;
                const res = this.snippets[val.slice(start, end)];
                if (res !== undefined) {
                    this.feedback = val.slice(0, start) + res.value + this.feedback.slice(end);
                }
                if (Math.random() < 0.25) {
                    this.refreshSnippets();
                }
            }
        },

        maybeSaveFeedback(event) {
            if (this.manualSave) {
                event.preventDefault();
                this.manualSave = false;
            } else if (this.feedbackChanged) {
                event.preventDefault();
                this.confirmMsg =
                    'Do you want to save the changes? Clicking "no" will discard your changes.';
                this.$afterRerender(this.$refs.submitButton.onClick);
            }
        },

        maybeHidePopover(event, force = false) {
            if (force || this.confirmMsg !== '') {
                this.$root.$emit('bv::hide::popover', this.popoverId);
            }
            this.reset();
            // We need to focus something in the popover to make the popover "blur" work.
            // https://github.com/bootstrap-vue/bootstrap-vue/issues/4548
            this.focusTextarea();
        },

        focusTextarea() {
            this.$refs.textarea.focus();
        },

        reset() {
            this.feedback = this.$utils.getProps(this.submission, '', 'comment');
            this.confirmMsg = '';
            this.manualSave = false;
        },
    },

    components: {
        Icon,
        User,
        SubmitButton,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.feedback-field {
    .default-text-colors;
    margin-bottom: 0;
    padding: 0.375rem 0.75rem;
    white-space: pre-wrap;
    text-align: left;
}

textarea {
    width: 25rem;
}
</style>
