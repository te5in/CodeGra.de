<template>
<div class="peer-feedback-settings">
    <div v-if="!enabled"
         class="d-flex flex-row justify-content-between">
        <b class="align-self-center">
            Enable peer feedback
        </b>

        <cg-submit-button :submit="enable"
                          @after-success="afterSubmit"
                          label="Enable"
                          class="my-n1"/>
    </div>

    <template v-else>
        <b-form-fieldset>
            <b-input-group>
                <b-input-group-prepend is-text>
                    Amount of students

                    <cg-description-popover hug-text>
                        The amount of students that each student must review.
                    </cg-description-popover>
                </b-input-group-prepend>
                <cg-number-input v-model="amount"
                                 @keyup.ctrl.enter.native="doSubmit"/>
            </b-input-group>
        </b-form-fieldset>

        <b-form-fieldset>
            <b-input-group prepend="">
                <b-input-group-prepend is-text>
                    Time to give peer feedback (days)

                    <cg-description-popover hug-text>
                        The amount of time students have to give feedback on the
                        submissions they were assigned, after the deadline of
                        this assignment has passed.
                    </cg-description-popover>
                </b-input-group-prepend>
                <cg-number-input v-model="time"
                                 @keyup.ctrl.enter.native="doSubmit"/>
            </b-input-group>
        </b-form-fieldset>

        <b-button-toolbar class="justify-content-end">
            <cg-submit-button :submit="disable"
                              @after-success="afterDisable"
                              variant="danger"
                              label="Disable"
                              class="mr-2"/>
            <cg-submit-button :submit="submit"
                              @after-success="afterSubmit"
                              ref="submitButton"/>
        </b-button-toolbar>
    </template>
</div>
</template>

<script lang="ts">
import { Vue, Component, Prop } from 'vue-property-decorator';
import { mapActions } from 'vuex';

import * as models from '@/models';

// @ts-ignore
import Toggle from './Toggle';

function daysToSeconds(days?: number | null): number | null {
    if (days == null) {
        return null;
    }
    return days * 24 * 60 * 60;
}

function secondsToDays(secs?: number | null): number | null {
    if (secs == null) {
        return null;
    }
    return secs / 24 / 60 / 60;
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

    time: number | null = secondsToDays(this.peerFeedbackSettings?.time) ?? 0;

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
        this.time = 7;
        this.amount = 1;
        return this.submit();
    }

    submit() {
        return this.$http.put(this.url, {
            time: daysToSeconds(this.time),
            amount: this.amount,
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
}
</script>
