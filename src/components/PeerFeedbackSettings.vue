<template>
<div class="peer-feedback-settings">
    <b-form-group>
        <label class="font-weight-bold">
            Peer feedback
        </label>
        <toggle v-model="enabled"
                class="float-right"
                label-on="Enabled"
                label-off="Disabled"/>
    </b-form-group>

    <template v-if="enabled">
        <b-form-fieldset>
            <b-input-group prepend="Amount">
                <cg-number-input v-model="amount" />
            </b-input-group>
        </b-form-fieldset>
    </template>

    <template v-if="enabled">
        <b-form-fieldset>
            <b-input-group prepend="Auto approved score">
                <cg-number-input v-model="autoApprovedScore" />
            </b-input-group>
        </b-form-fieldset>
    </template>

    <template v-if="enabled">
        <b-form-fieldset>
            <b-input-group prepend="Time (seconds)">
                <cg-number-input v-model="time" />
            </b-input-group>
        </b-form-fieldset>
    </template>

    <cg-submit-button :submit="submit"
                       />
</div>
</template>

<script lang="ts">
import { Vue, Component, Prop } from 'vue-property-decorator';

import * as models from '@/models';

// @ts-ignore
import Toggle from './Toggle';

@Component({
    components: {
        Toggle,
    },
})
export default class PeerFeedbackSettings extends Vue {
    @Prop({ required: true }) assignment!: models.Assignment;

    get peerFeedbackSettings(): null | any {
        return this.assignment.peer_feedback_settings;
    }

    enabled: boolean = this.peerFeedbackSettings != null;

    amount: number | null = this.peerFeedbackSettings?.amount ?? 0;

    time: number | null = this.peerFeedbackSettings?.amount ?? 0;

    autoApprovedScore: number | null = this.peerFeedbackSettings?.autoApprovedScore ?? 0;

    submit() {
        return this.$http.put(`/api/v1/assignments/${this.assignment.id}/peer_feedback_settings`, {
            time: this.time,
            amount: this.amount,
            auto_approved_score: this.autoApprovedScore,
        });
    }
}
</script>
