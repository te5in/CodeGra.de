<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template functional>
<span v-if="props.submission.isLate()"
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
import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/clock-o';

import { Assignment } from '@/models';

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
            type: Assignment,
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
                const diff = props.submission.createdAt.from(
                    props.assignment.deadline,
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
