<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<component :is="btn ? 'b-btn' : 'span'"
           class="auto-test-state"
           variant="secondary" >
    <span v-b-popover.hover.top="readable">
        <span v-if="state == 'running'" class="running">
            <template v-if="!noTimer">
                {{ minutes }}:{{ seconds }}
            </template>
        </span>
        <icon v-else-if="showIcon && icon"
              :class="iconClass"
              :name="icon" />
    </span>

    <template v-if="btn">{{ readable }}</template><slot name="extra" v-if="$slots.extra"/>
</component>
</template>

<script>
import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/ban';
import 'vue-awesome/icons/check';
import 'vue-awesome/icons/times';
import 'vue-awesome/icons/clock-o';
import 'vue-awesome/icons/exclamation-triangle';

export default {
    name: 'auto-test-state',

    props: {
        result: {
            type: Object,
            default: null,
        },
        btn: {
            type: Boolean,
            default: false,
        },
        noTimer: {
            type: Boolean,
            default: false,
        },
        showIcon: {
            type: Boolean,
            default: false,
        },
    },

    computed: {
        state() {
            return this.$utils.getProps(this.result, 'not_started', 'state');
        },

        icon() {
            switch (this.state) {
                case 'passed':
                case 'done':
                    return 'check';
                case 'partial':
                    return 'tilde';
                case 'failed':
                    return 'times';
                case 'hidden':
                case 'skipped':
                    return 'ban';
                case 'starting':
                case 'not_started':
                case 'waiting_for_runner':
                    return 'clock-o';
                case 'timed_out':
                case 'crashed':
                    return 'exclamation-triangle';
                default:
                    return '';
            }
        },

        iconClass() {
            switch (this.state) {
                case 'passed':
                case 'done':
                    return 'text-success';
                case 'failed':
                case 'timed_out':
                case 'crashed':
                    return 'text-danger';
                case 'hidden':
                case 'skipped':
                    return 'text-muted';
                default:
                    return '';
            }
        },

        readable() {
            switch (this.state) {
                case 'hidden':
                    return "This step is hidden and will not be executed until the assignment's deadline has passed.";
                case 'not_started':
                    return 'Waiting to be started';
                default:
                    return this.$utils.capitalize(this.state.replace(/_/g, ' '));
            }
        },

        passedSinceStart() {
            return Math.max(0, this.$root.$epoch.diff(this.result.startedAt, 'seconds'));
        },

        minutes() {
            return this.$utils.formatTimePart(Math.floor(this.passedSinceStart / 60));
        },

        seconds() {
            return this.$utils.formatTimePart(Math.floor(this.passedSinceStart % 60));
        },
    },

    components: {
        Icon,
    },
};
</script>

<style lang="less" scoped>
.auto-test-state.btn {
    pointer-events: none;
}
</style>
