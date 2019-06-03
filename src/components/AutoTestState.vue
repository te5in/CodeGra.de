<template>
<component :is="btn ? 'b-btn' : 'span'"
           class="auto-test-state"
           variant="secondary" >
    <span v-b-popover.hover.top="popover">
        <icon :class="iconClass"
              :name="icon"
              :spin="icon == 'circle-o-notch'"
              v-if="icon" />
    </span>

    <template v-if="btn">
        {{ $capitalize(state.replace(/_/g, ' ')) }}
    </template>
</component>
</template>

<script>
import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/ban';
import 'vue-awesome/icons/check';
import 'vue-awesome/icons/times';
import 'vue-awesome/icons/clock-o';
import 'vue-awesome/icons/circle-o-notch';

export default {
    name: 'auto-test-state',

    props: {
        state: {
            type: String,
            required: true,
        },

        btn: {
            type: Boolean,
            default: false,
        },
    },

    computed: {
        icon() {
            switch (this.state) {
                case 'passed':
                case 'done':
                    return 'check';
                case 'failed':
                case 'crashed':
                    return 'times';
                case 'skipped':
                    return 'ban';
                case 'not_started':
                    return 'clock-o';
                case 'running':
                    return 'circle-o-notch';
                case 'timed_out':
                    return 'exclamation-triangle';
                default:
                    return '';
            }
        },

        iconClass() {
            switch (this.state) {
                case 'passed':
                    return 'text-success';
                case 'failed':
                case 'timed_out':
                case 'crashed':
                    return 'text-danger';
                case 'skipped':
                    return 'text-muted';
                default:
                    return '';
            }
        },

        popover() {
            switch (this.state) {
                case 'passed':
                    return 'Passed!';
                case 'failed':
                    return 'Failed';
                case 'skipped':
                    return 'Skipped';
                case 'not_started':
                    return 'Waiting to be started';
                case 'running':
                    return 'Running...';
                case 'timed_out':
                    return 'Timed out.';
                case 'done':
                    return 'Done';
                case 'crashed':
                    return 'Crashed';
                default:
                    return '';
            }
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
