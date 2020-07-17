<template>
<div class="peer-feedback-settings">
    <div v-if="!enabled"
         class="d-flex flex-row justify-content-between">
        <b class="align-self-center">
            Enable peer feedback
        </b>

        <div v-b-popover.hover.top="submitDisabledMessage">
            <cg-submit-button
                :disabled="!!submitDisabledMessage"
                :submit="enable"
                @after-success="afterSubmit"
                label="Enable"
                class="my-n1"/>
        </div>
    </div>

    <template v-else>
        <b-form-fieldset label="Amount of students">
            <template #label>
                Amount of students

                <cg-description-popover hug-text>
                    The amount of students that each student must review.
                </cg-description-popover>
            </template>
            <b-input-group>
                <cg-number-input v-model="amount"
                                 :min="1"
                                 @keyup.ctrl.enter.native="doSubmit"/>
            </b-input-group>
        </b-form-fieldset>

        <b-form-fieldset>
            <template #label>
                Time to give peer feedback

                <cg-description-popover hug-text>
                    The amount of time students have to give feedback on the
                    submissions they were assigned, after the deadline of
                    this assignment has passed.
                </cg-description-popover>
            </template>

            <b-input-group>
                <cg-number-input v-model="days"
                                 :min="0"
                                 @keyup.ctrl.enter.native="doSubmit"/>

                <b-input-group-prepend is-text>
                    Days
                </b-input-group-prepend>

                <cg-number-input v-model="hours"
                                 :min="0"
                                 @keyup.ctrl.enter.native="doSubmit"/>

                <b-input-group-prepend is-text>
                    Hours
                </b-input-group-prepend>
            </b-input-group>
        </b-form-fieldset>

        <b-form-fieldset class="mt-4">
            <label>
                Auto approve comments

                <cg-description-popover hug-text>
                    Should new peer feedback comments be automatically
                    approved. Changing this value does not change the
                    approval status of existing comments.
                </cg-description-popover>
            </label>

            <cg-toggle v-model="autoApproved"
                       class="float-right"
                       label-on="Yes"
                       label-off="No" />
        </b-form-fieldset>

        <b-button-toolbar class="justify-content-end">
            <cg-submit-button :submit="disable"
                              @after-success="afterDisable"
                              confirm="Are you sure you want to disable peer feedback?"
                              variant="danger"
                              label="Disable"
                              class="mr-2"/>
            <cg-submit-button :submit="submit"
                              @after-success="afterSubmit"
                              :confirm="submitConfirmationMessage"
                              ref="submitButton"/>
        </b-button-toolbar>
    </template>
</div>
</template>

<script lang="ts">
import { Vue, Component, Prop } from 'vue-property-decorator';
import { mapActions } from 'vuex';

import * as utils from '@/utils';
import * as models from '@/models';

// @ts-ignore
import Toggle from './Toggle';

function hoursToSeconds(hours: number): number {
    return hours * 60 * 60;
}

function daysToSeconds(days: number): number {
    return hoursToSeconds(days * 24);
}

function secondsToDays(secs?: number | null): number | null {
    return secs == null ? null : Math.floor(secs / daysToSeconds(1));
}

function secondsToHours(secs?: number | null): number | null {
    return secs == null ? null : (secs % daysToSeconds(1)) / 60 / 60;
}

@Component({
    methods: {
        ...mapActions('courses', ['updateAssignment']),
    },
    components: {
        Toggle,
    },
})
export default class PeerFeedbackSettings extends Vue {
    @Prop({ required: true }) assignment!: models.Assignment;

    get peerFeedbackSettings(): null | models.AssignmentPeerFeedbackSettings {
        return this.assignment.peer_feedback_settings;
    }

    get enabled(): boolean {
        return this.peerFeedbackSettings != null;
    }

    amount: number | null = this.peerFeedbackSettings?.amount ?? 0;

    days: number | null = secondsToDays(this.peerFeedbackSettings?.time);

    hours: number | null = secondsToHours(this.peerFeedbackSettings?.time);

    get time() {
        const days = this.$utils.getProps(this, 0, 'days');
        const hours = this.$utils.getProps(this, 0, 'hours');
        return daysToSeconds(days) + hoursToSeconds(hours);
    }

    // eslint-disable-next-line camelcase
    autoApproved: boolean = this.peerFeedbackSettings?.auto_approved ?? false;

    updateAssignment!: (data: {
        assignmentId: number,
        assignmentProps: models.AssignmentUpdateableProps
    }) => void;

    updatePeerFeedbackSettings(settings: models.AssignmentPeerFeedbackSettings | null): void {
        this.updateAssignment({
            assignmentId: this.assignment.id,
            assignmentProps: { peer_feedback_settings: settings },
        });
    }

    get url() {
        return `/api/v1/assignments/${this.assignment.id}/peer_feedback_settings`;
    }

    enable() {
        this.days = 7;
        this.hours = 0;
        this.amount = 1;
        this.autoApproved = false;
        return this.submit();
    }

    submit() {
        this.validateSettings();
        return this.$http.put(this.url, {
            time: daysToSeconds(this.time),
            amount: this.amount,
            auto_approved: this.autoApproved,
        });
    }

    afterSubmit(res: any) {
        this.updatePeerFeedbackSettings(res.data);
    }

    disable() {
        return this.$http.delete(this.url);
    }

    afterDisable() {
        this.updatePeerFeedbackSettings(null);
    }

    async doSubmit() {
        const btn = await this.$waitForRef('submitButton');
        if (btn != null) {
            btn.onClick();
        }
    }

    get submitDisabledMessage() {
        if (this.assignment.group_set == null) {
            return '';
        }
        return `This is a group assignment, but peer feedback is not yet
            supported for group assignments.`;
    }

    get submitConfirmationMessage() {
        if (this.amount != null && this.peerFeedbackSettings?.amount !== this.amount) {
            return `Changing the amount of students will redistribute all
                students. If some students have already given peer feedback to
                other students they will not be able to see their own given
                feedback again, although it is not deleted from the server
                either. Are you sure you want to change it?`;
        } else {
            return '';
        }
    }

    validateSettings(): void {
        const errs = utils.mapFilterObject({
            amount: this.ensurePositive(this.amount),
            time: this.ensurePositive(this.time),
        }, (v: string, k: string) => {
            if (!v) {
                return utils.Nothing;
            } else {
                return utils.Just(`${k} ${v}`);
            }
        });

        if (!utils.isEmpty(errs)) {
            const msgs = Object.values(errs).join(', ');
            throw new Error(`The peer feedback settings are not valid because: ${msgs}.`);
        }
    }

    // eslint-disable-next-line class-methods-use-this
    ensurePositive(value: number | null): string {
        if (typeof value !== 'number') {
            return 'is not a number';
        }
        if (value < 0) {
            return 'is not positive';
        }
        return '';
    }
}
</script>
