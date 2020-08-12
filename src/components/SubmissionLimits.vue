<template>
<div class="submission-limits" v-if="value != null">
    <b-form-fieldset :id="`assignment-max-submissions-${uniqueId}`"
                     :label-for="`assignment-max-submissions-${uniqueId}-input`">
        <template #label>
            Maximum total amount of submissions
        </template>

        <template #description>
            The maximum amount of submissions students will be able to make.

            <cg-description-popover hug-text>
                If you leave this value empty, or set it to 0, students will be
                able to make an infinite amount of submissions.
            </cg-description-popover>
        </template>

        <cg-number-input
            :id="`assignment-max-submissions-${uniqueId}-input`"
            :min="0"
            @keyup.ctrl.enter="$emit('update-max-submissions')"
            :value="maxSubmissions"
            @input="maxSubmissions = $event"
            placeholder="Infinite"/>
    </b-form-fieldset>

    <b-form-fieldset :id="`assignment-cool-off-${uniqueId}`"
                     :label-for="`assignment-cool-off-${uniqueId}-input`"
                     :state="coolOffAmount != null && coolOffPeriod != null">
        <template #label>
            Cool off period
        </template>

        <template #description>
            The minimum amount of time there should be between submissions.

            <cg-description-popover hug-text>
                The first input determines the amount of submissions, and the
                second the time in minutes. You can set the time to zero to
                disable this limit.
            </cg-description-popover>
        </template>

        <template #invalid-feedback>
            <div v-if="coolOffAmount == null">
                The amount of submissions must be a positive number.
            </div>
            <div v-if="coolOffPeriod == null">
                The period must be a number greater than or equal to 0.
            </div>
        </template>

        <b-input-group class="cool-off-period-wrapper">
            <cg-number-input
                :id="`assignment-cool-off-${uniqueId}-input`"
                class="amount-in-cool-off-period"
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

    readonly uniqueId: number = this.$utils.getUniqueId();

    get coolOffValid() {
        return this.coolOffPeriod != null && this.coolOffAmount != null;
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
