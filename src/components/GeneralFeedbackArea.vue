<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="general-feedback-area">
    <textarea :placeholder="placeholder"
              class="form-control"
              :rows="10"
              ref="field"
              v-model="feedback"
              @keydown.ctrl.enter.prevent="$refs.submitButton.onClick"
              @keydown.native.tab.capture="expandSnippet"
              v-if="editable"/>
    <pre class="feedback-field"
         v-else>{{ feedback || placeholder }}</pre>
    <submit-button ref="submitButton"
                   :submit="submitFeedback"
                   @success="afterSubmitFeedback"
                   v-if="editable"
                   style="margin: 15px 0; float: right;"/>
</div>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';

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
    },

    computed: {
        ...mapGetters('user', {
            nameCurrentUser: 'name',
            userId: 'id',
        }),

        placeholder() {
            return this.feedback || 'No feedback given :(';
        },
    },

    data() {
        return {
            feedback: this.submission.comment,
        };
    },

    watch: {
        submission() {
            this.feedback = this.submission.comment || '';
        },
    },

    methods: {
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
            const { field } = this.$refs;
            const end = field.$el.selectionEnd;
            if (field.$el.selectionStart === end) {
                event.preventDefault();
                const val = this.feedback.slice(0, end);
                const start = Math.max(val.lastIndexOf(' '), val.lastIndexOf('\n')) + 1;
                const res = this.snippets()[val.slice(start, end)];
                if (res !== undefined) {
                    this.feedback = val.slice(0, start) + res.value + this.feedback.slice(end);
                }
                if (Math.random() < 0.25) {
                    this.refreshSnippets();
                }
            }
        },
    },

    components: {
        SubmitButton,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.feedback-field {
    margin-bottom: 0;
    padding: 0.375rem 0.75rem;
    white-space: pre-wrap;
    text-align: left;
    .default-text-colors;
}
</style>
