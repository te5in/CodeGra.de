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

    <submit-button class="float-right"
                   :submit="() => submitDeepLinkRequest()"
                   label="Create assignment" />
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
            name: this.initialAssignmentName,
            deadline: this.initialAssignmentDeadline,
            submissionLimits: {
                maxSubmissions: null,
                coolOff: {
                    amount: 0,
                    period: 0,
                },
            },
            submitTypes: null,
        };
    },

    methods: {
        submitDeepLinkRequest() {
            return {};
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
