<template>
<component :is="btn ? 'b-btn' : 'span'"
           class="auto-test-state"
           variant="secondary" >
    <span v-b-popover.hover.top="readable">
        <div v-if="state == 'running'" class="running">
            <template v-if="showTimer">
                {{ minutes }}:{{ seconds }}
            </template>
        </div>
        <icon v-else-if="icon"
              :class="iconClass"
              :name="icon" />
    </span>

    <template v-if="btn">
        {{ readable }}
    </template>
</component>
</template>

<script>
import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/ban';
import 'vue-awesome/icons/check';
import 'vue-awesome/icons/times';
import 'vue-awesome/icons/clock-o';
import 'vue-awesome/icons/exchange';
import 'vue-awesome/icons/exclamation-triangle';

export default {
    name: 'auto-test-state',

    props: {
        result: {
            type: Object,
            required: true,
        },

        btn: {
            type: Boolean,
            default: false,
        },

        noTimer: {
            type: Boolean,
            default: false,
        },
    },

    data() {
        return {
            minutes: null,
            seconds: null,
        };
    },

    computed: {
        state() {
            return this.$utils.getProps(this.result, 'not_started', 'state');
        },

        startMSec() {
            let startMSec = this.$utils.getProps(this.result, null, 'startedAt');
            if (startMSec) startMSec = startMSec.valueOf();
            return startMSec;
        },

        icon() {
            switch (this.state) {
                case 'passed':
                case 'done':
                    return 'check';
                case 'failed':
                    return 'times';
                case 'skipped':
                    return 'ban';
                case 'starting':
                case 'not_started':
                case 'waiting_for_runner':
                    return 'clock-o';
                case 'changing_runner':
                    return 'exchange';
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

        readable() {
            switch (this.state) {
                case 'not_started':
                    return 'Waiting to be started';
                default:
                    return this.$utils.capitalize(this.state.replace(/_/g, ' '));
            }
        },

        showTimer() {
            return !this.noTimer && this.minutes != null && this.seconds != null;
        },
    },

    methods: {
        updateEpoch(epoch) {
            if (this.startMSec != null) {
                const duration = (epoch - this.startMSec) / 1000;
                this.minutes = this.$utils.formatTimePart(Math.floor(duration / 60));
                this.seconds = this.$utils.formatTimePart(Math.floor(duration % 60));
            }
        },
    },

    mounted() {
        if (!this.noTimer) {
            this.$root.$on('epoch', this.updateEpoch);
        }
    },

    destroyed() {
        if (!this.noTimer) {
            this.$root.$off('epoch', this.updateEpoch);
        }
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
