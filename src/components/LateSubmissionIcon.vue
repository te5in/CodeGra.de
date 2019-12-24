<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template functional>
<span v-if="props.submission.formatted_created_at > props.assignment.formatted_deadline"
      class="late-submission-icon active">
    <component
        :is="injections.components.Icon"
        name="clock-o"
        :scale="props.scale"
        class="late-icon"
        :class="{ 'with-popover': !props.hidePopover }"
        v-b-popover.hover.top="props.hidePopover ? '' : props.getHandedInLateText(props)"/>
</span>
<span v-else class="late-submission-icon non-active" :class="data.class"/>
</template>

<script>
import moment from 'moment';
import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/clock-o';

export default {
    name: 'late-submission-icon',

    inject: {
        components: {
            default: {
                Icon,
            },
        },
    },

    props: {
        submission: {
            type: Object,
            required: true,
        },

        assignment: {
            type: Object,
            required: true,
        },

        hidePopover: {
            type: Boolean,
            default: false,
        },

        scale: {
            type: Number,
            default: 1,
        },

        getHandedInLateText: {
            type: Function,
            default: props => {
                const diff = moment(props.submission.formatted_created_at, moment.ISO_8601).from(
                    moment(props.assignment.formatted_deadline, moment.ISO_8601),
                    true, // Only get time string, not the 'in' before.
                );
                return `This submission was submitted ${diff} after the deadline.`;
            },
        },
    },
};
</script>

<style lang="less" scoped>
.late-submission-icon.active {
    .late-icon {
        margin-bottom: -0.125em;
        text-decoration: bold;
        &.with-popover {
            cursor: help;
        }
    }
}
</style>
