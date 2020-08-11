<template>
<div class="submission-limits" v-if="value != null">
    <b-form-fieldset>
        <template #label>
            Maximum total amount of submissions

            <cg-description-popover hug-text>
                The maximum amount of submissions, inclusive, students will
                be able to make. If you leave this value empty,
                or set it to 0, students will be able to make an
                infinite amount of submissions.
            </cg-description-popover>
        </template>

        <cg-number-input
            :min="0"
            @keyup.ctrl.enter="$emit('update-max-submissions')"
            :value="maxSubmissions"
            @input="maxSubmissions = $event"
            placeholder="Infinite"/>
    </b-form-fieldset>

    <b-form-fieldset
        :state="!coolOffFeedback"
        :invalid-feedback="coolOffFeedback">
        <template #label>
            Cool off period

            <cg-description-popover hug-text>
                The minimum amount of time there should be
                between submissions. The first input determines
                the amount of submissions, and the second the
                time in minutes. You can set the time to zero to
                disable this limit.
            </cg-description-popover>
        </template>

        <b-input-group class="cool-off-period-wrapper">
            <cg-number-input class="amount-in-cool-off-period"
                :min="1"
                @keyup.ctrl.enter="$emit('update-cool-off')"
                :value="coolOffAmount"
                @input="coolOffAmount = $event"/>

            <b-input-group-prepend is-text>
                <template v-if="parseFloat(coolOffAmount) === 1">
                    submission
                </template>
                <template v-else>
                    submissions
                </template>
                every
            </b-input-group-prepend>

            <cg-number-input
                class="cool-off-period"
                :min="0"
                :step="1"
                @keyup.ctrl.enter="$emit('update-cool-off')"
                :value="coolOffPeriod"
                @input="coolOffPeriod = $event"
                placeholder="0"/>

            <b-input-group-append is-text>
                <template v-if="parseFloat(coolOffPeriod) === 1">
                    minute
                </template>
                <template v-else>
                    minutes
                </template>
            </b-input-group-append>

            <slot name="cool-off-period" />
        </b-input-group>
    </b-form-fieldset>
</div>
</template>

<script lang="ts">
import { Vue, Component, Prop, Watch } from 'vue-property-decorator';

type MaxSubmissions = number | null;
type CoolOff = {
    period: number,
    amount: number;
};

export type SubmissionLimitValue = {
    maxSubmissions: MaxSubmissions,
    coolOff: CoolOff,
};

@Component
export default class SubmissionLimits extends Vue {
    @Prop({ required: true })
    value!: SubmissionLimitValue;

    maxSubmissions: number | null = null;

    coolOffPeriod: number | null = 0;

    coolOffAmount: number | null = 1;

    get coolOffValid() {
        return this.coolOffPeriod != null && this.coolOffAmount != null;
    }

    get coolOffFeedback() {
        let fb = '';

        if (this.coolOffAmount == null) {
            fb += 'The amount of submissions must be a positive number. ';
        }

        if (this.coolOffPeriod == null) {
            fb += 'The period must be a number greater than or equal to 0.';
        }

        return fb;
    }

    @Watch('value', { immediate: true })
    onValueChanged() {
        if (this.value != null) {
            this.maxSubmissions = this.value.maxSubmissions;
            this.coolOffPeriod = this.value.coolOff.period;
            this.coolOffAmount = this.value.coolOff.amount;
        } else {
            this.emitValue();
        }
    }

    @Watch('maxSubmissions')
    @Watch('coolOffPeriod')
    @Watch('coolOffAmount')
    emitValue() {
        this.$emit('input', {
            maxSubmissions: this.maxSubmissions,
            coolOff: {
                period: this.coolOffPeriod,
                amount: this.coolOffAmount,
            },
        });
    }
}
</script>
