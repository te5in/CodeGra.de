<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<b-card v-if="permissions.canEditSubmissionSettings"
        header="Submission settings"
        class="assignment-submission-settings">
    <b-form-group
        :state="submitTypesValid"
        invalid-feedback="Enable at least one way of uploading.">
        <template #label>
            Allowed upload types

            <cg-description-popover hug-text>
                Select how you want your student to hand in
                their submissions. You can either select a file
                uploader, via a GitHub/GitLab webhook, or both.
            </cg-description-popover>
        </template>

        <assignment-submit-types
            :assignment-id="assignmentId"
            v-model="submitTypes" />
    </b-form-group>

    <submission-limits
        v-model="submissionLimits"
        @keydown.ctrl.enter.native="$refs.submitSubmissionSettings.onClick()" />

    <div class="float-right"
         v-b-popover.top.hover="submitButtonPopover">
        <cg-submit-button
            ref="submitSubmissionSettings"
            :disabled="!!submitButtonPopover"
            :submit="submitSubmissionSettings" />
    </div>
</b-card>
</template>

<script lang="ts">
import { Vue, Component, Prop, Watch } from 'vue-property-decorator';
import { mapActions } from 'vuex';
import { AxiosResponse } from 'axios';

import * as models from '@/models';

// @ts-ignore
import AssignmentSubmitTypes, { AssignmentSubmitTypesValue } from './AssignmentSubmitTypes';
// @ts-ignore
import SubmissionLimits, { SubmissionLimitValue } from './SubmissionLimits';

@Component({
    components: {
        AssignmentSubmitTypes,
        SubmissionLimits,
    },
    methods: {
        ...mapActions('courses', [
            'updateAssignmentSubmissionSettings',
        ]),
    },
})
export default class AssignmentGeneralSettings extends Vue {
    @Prop({ required: true })
    assignment!: models.Assignment

    submitTypes: AssignmentSubmitTypesValue | null = null;

    submissionLimits: SubmissionLimitValue | null = null;

    updateAssignmentSubmissionSettings!:
        (args: any) => Promise<AxiosResponse<void>>;

    get assignmentId() {
        return this.assignment.id;
    }

    @Watch('assignmentId', { immediate: true })
    onAssignmentChanged() {
        this.submitTypes = {
            files: this.assignment.files_upload_enabled,
            webhook: this.assignment.webhook_upload_enabled,
        };
        this.submissionLimits = {
            maxSubmissions: this.assignment.max_submissions,
            coolOff: {
                period: this.assignment.coolOffPeriod.asMinutes(),
                amount: this.assignment.amount_in_cool_off_period,
            },
        };
    }

    get permissions() {
        return new models.AssignmentCapabilities(this.assignment);
    }

    get nothingChanged() {
        const st = this.submitTypes;
        const sl = this.submissionLimits;

        if (st != null) {
            if (st.files !== this.assignment.files_upload_enabled) {
                return false;
            }
            if (st.webhook !== this.assignment.webhook_upload_enabled) {
                return false;
            }
        }
        if (sl != null) {
            if (sl.maxSubmissions !== this.assignment.max_submissions) {
                return false;
            }
            if (sl.coolOff.period !== this.assignment.coolOffPeriod.asMinutes()) {
                return false;
            }
            if (sl.coolOff.amount !== this.assignment.amount_in_cool_off_period) {
                return false;
            }
        }

        return true;
    }

    get submitTypesValid() {
        const st = this.submitTypes;
        return st.files || st.webhook;
    }

    get submissionLimitsValid() {
        const sl = this.submissionLimits;
        return sl != null && sl.coolOff.amount != null;
    }

    get allDataValid() {
        return this.submitTypesValid && this.submissionLimitsValid;
    }

    get submitButtonPopover() {
        if (this.nothingChanged) {
            return 'Nothing has changed.';
        } else if (!this.allDataValid) {
            return 'Cannot submit while some data is invalid.';
        } else {
            return '';
        }
    }

    submitSubmissionSettings() {
        if (this.submitTypes == null || this.submissionLimits == null) {
            return Promise.reject();
        }

        return this.updateAssignmentSubmissionSettings({
            assignmentId: this.assignment.id,
            filesUploadEnabled: this.submitTypes.files,
            webhookUploadEnabled: this.submitTypes.webhook,
            maxSubmissions: this.submissionLimits.maxSubmissions,
            coolOffPeriod: this.submissionLimits.coolOff.period,
            coolOffAmount: this.submissionLimits.coolOff.amount,
        });
    }
}
</script>
