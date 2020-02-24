<template>
<div class="lti-deep-link">
    <b-form-fieldset>
        <b-input-group prepend="Name">
            <input class="form-control"
                   v-model="name"
                   placeholder="The name of the new assignment" />
        </b-input-group>
    </b-form-fieldset>

    <b-form-fieldset>
        <b-input-group prepend="Deadline">
            <datetime-picker v-model="deadline"
                             placeholder="The deadline of the new assignment"/>
        </b-input-group>
    </b-form-fieldset>

    <b-form-fieldset>
        <assignment-submit-types
            :assignment-id="null"
            v-model="submitTypes" />
    </b-form-fieldset>

    <submission-limits v-model="submissionLimits" />

    <div class="float-right"
         v-b-popover.top.hover="submitPopover">
        <submit-button :disabled="!!submitPopover"
                       :submit="() => submitDeepLinkRequest()"
                       @after-success="afterSubmitDeepLinkRequest"
                       label="Create assignment" />
    </div>

    <template v-if="formData">
        <form :action="formData.url"
              method="POST"
              ref="linkForm">
            <input type="hidden" name="JWT" :value="formData.jwt" />
        </form>
    </template>
</div>
</template>

<script>
import SubmissionLimits from './SubmissionLimits';
import DatetimePicker from './DatetimePicker';
import AssignmentSubmitTypes from './AssignmentSubmitTypes';
import SubmitButton from './SubmitButton';

export default {
    name: 'lti-deep-link',

    props: {
        initialAssignmentName: {
            type: String,
            required: true,
        },

        initialAssignmentDeadline: {
            type: String,
            required: true,
        },

        autoCreate: {
            type: Boolean,
            required: true,
        },

        deepLinkId: {
            type: String,
            required: true,
        },
    },

    data() {
        return {
            formData: null,
            name: this.initialAssignmentName,
            deadline: this.initialAssignmentDeadline,
            submissionLimits: {
                maxSubmissions: null,
                coolOff: {
                    amount: 1,
                    period: 0,
                },
            },
            submitTypes: null,
        };
    },

    computed: {
        submitPopover() {
            if (!this.deadline) {
                return 'A deadline is required';
            }
            return '';
        },
    },

    methods: {
        submitDeepLinkRequest() {
            return this.$http.post(`/api/v1/lti1.3/deep_link/${this.deepLinkId}/assignment`, {
                name: this.name,
                deadline: this.deadline,
                max_submissions: parseFloat(this.submissionLimits.maxSubmissions),
                cool_off_period: parseFloat(this.submissionLimits.coolOff.period),
                amount_in_cool_off_period: parseFloat(this.submissionLimits.coolOff.amount),
            });
        },

        async afterSubmitDeepLinkRequest({ data }) {
            this.formData = data;
            await this.$afterRerender();
            console.log(this.$refs.linkForm);
            this.$refs.linkForm.submit();
        },
    },

    components: {
        SubmissionLimits,
        DatetimePicker,
        AssignmentSubmitTypes,
        SubmitButton,
    },
};
</script>
