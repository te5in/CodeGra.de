<template>
<div class="submission-limits" v-if="value != null">
    <b-form-fieldset>
        <b-input-group class="max-submissions">
            <b-input-group-prepend is-text slot="prepend">
                Maximum amount of submissions
                <description-popover>
                    The maximum amount of submissions, inclusive, students will
                    be able to make. If you leave this value empty,
                    or set it to 0, students will be able to make an
                    infinite amount of submissions.
                </description-popover>
            </b-input-group-prepend>

            <input class="form-control"
                type="number"
                min="0"
                @keyup.ctrl.enter="$emit('update-max-submissions')"
                :value="value.maxSubmissions"
                @input="emitUpdate({ maxSubmissions: $event.target.value })"
                placeholder="Infinite"/>

            <slot name="max-submissions" />
        </b-input-group>
    </b-form-fieldset>

    <b-form-fieldset>
        <b-input-group class="cool-off-period-wrapper">
            <b-input-group-prepend is-text slot="prepend">
                Cool off period
                <description-popover>
                    The minimum amount of time there should be
                    between submissions. The first input determines
                    the amount of submissions, and the second the
                    time in minutes. You can set the time to zero to
                    disable this limit.
                </description-popover>
            </b-input-group-prepend>

            <input class="form-control amount-in-cool-off-period"
                type="number"
                min="0"
                @keyup.ctrl.enter="$emit('update-cool-off')"
                :value="value.coolOff.amount"
                @input="emitUpdate({ coolOff: { amount: $event.target.value } })" />

            <b-input-group-prepend is-text>
                <template v-if="parseFloat(value.coolOff.amount) === 1">
                    submission
                </template>
                <template v-else>
                    submissions
                </template>
                every
            </b-input-group-prepend>

            <input class="form-control cool-off-period"
                type="number"
                min="0"
                step="1"
                @keyup.ctrl.enter="$emit('update-cool-off')"
                @input="emitUpdate({ coolOff: { period: $event.target.value } })"
                :value="value.coolOff.period"
                placeholder="0"/>

            <b-input-group-append is-text>
                <template v-if="parseFloat(value.coolOff.period) === 1">
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


<script>
import DescriptionPopover from './DescriptionPopover';

export default {
    name: 'submission-limits',

    props: {
        value: {
            type: Object,
            required: true,
        },
    },

    data() {
        return {
            parseFloat,
        };
    },

    methods: {
        emitUpdate(data) {
            const updated = this.$utils.deepCopy(this.value);
            if (data.maxSubmissions) {
                updated.maxSubmissions = data.maxSubmissions;
            }
            if (data.coolOff) {
                Object.assign(updated.coolOff, data.coolOff);
            }

            this.$emit('input', updated);
        },
    },

    components: {
        DescriptionPopover,
    },
};
</script>
