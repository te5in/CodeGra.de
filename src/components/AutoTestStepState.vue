<template>
<icon
    class="auto-test-step-state"
    :class="className"
    :name="name"
    :spin="spin"
    v-b-popover.hover.top="popover"
/>
</template>

<script>
import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/check';
import 'vue-awesome/icons/times';
import 'vue-awesome/icons/clock-o';
import 'vue-awesome/icons/circle-o-notch';
import 'vue-awesome/icons/ban';

export default {
    name: 'auto-test-step-state',

    props: {
        state: {
            type: String,
            required: true,
        },
    },

    computed: {
        name() {
            switch (this.state) {
                case 'passed':
                    return 'check';
                case 'failed':
                    return 'times';
                case 'skipped':
                    return 'ban';
                case 'not_started':
                    return 'clock-o';
                case 'running':
                    return 'circle-o-notch';
                default:
                    return '';
            }
        },

        spin() {
            return this.name === 'circle-o-notch';
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
                default:
                    return '';
            }
        },

        className() {
            switch (this.state) {
                case 'passed':
                    return 'text-success';
                case 'failed':
                    return 'text-danger';
                case 'skipped':
                    return 'text-muted';
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
