<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="assignment-state" v-if="editable">
    <b-button-group>
        <submit-button class="state-button larger"
                       v-if="canManageLTIState"
                       :size="size"
                       :variant="ltiHiddenOpenVariant"
                       v-b-popover.window.top.hover="'Hidden or open, managed by LMS'"
                       :submit="() => updateState(states.OPEN)"
                       @success="afterUpdateState"
                       :icon-scale="iconScale"
                       :duration="0">
            <icon :name="icons[states.HIDDEN]" :scale="iconScale"/>
            <icon :name="icons[states.OPEN]" :scale="iconScale"/>
        </submit-button>

        <b-button-group v-else>
            <submit-button class="state-button"
                           :size="size"
                           :variant="hiddenVariant"
                           v-b-popover.window.top.hover="labels[states.HIDDEN]"
                           :submit="() => updateState(states.HIDDEN)"
                           @success="afterUpdateState"
                           :icon-scale="iconScale"
                           :duration="0">
                <icon :name="icons[states.HIDDEN]" :scale="iconScale"/>
            </submit-button>

            <submit-button class="state-button"
                           :size="size"
                           :variant="openVariant"
                           v-b-popover.window.top.hover="labels[states.OPEN]"
                           :submit="() => updateState(states.OPEN)"
                           @success="afterUpdateState"
                           :icon-scale="iconScale"
                           :duration="0">
                <icon :name="icons[states.OPEN]" :scale="iconScale"/>
            </submit-button>
        </b-button-group>

        <submit-button class="state-button"
                       :size="size"
                       :variant="doneVariant"
                       v-b-popover.window.top.hover="labels[states.DONE]"
                       :submit="() => updateState(states.DONE)"
                       @success="afterUpdateState"
                       :icon-scale="iconScale"
                       :duration="0">
            <icon :name="icons[states.DONE]" :scale="iconScale"/>
        </submit-button>
    </b-button-group>
</div>
<icon :name="icons[assignment.state]"
      class="assignment-state state-icon"
      v-b-popover.window.top.hover="labels[assignment.state]"
      v-else/>
</template>

<script>
import { mapActions } from 'vuex';

import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/eye-slash';
import 'vue-awesome/icons/clock-o';
import 'vue-awesome/icons/pencil';
import 'vue-awesome/icons/check';

import ltiProviders from '@/lti_providers';

import * as states from '../store/assignment-states';

import Loader from './Loader';
import SubmitButton from './SubmitButton';

export default {
    name: 'assignment-state',

    props: {
        assignment: {
            type: Object,
            default: null,
        },

        editable: {
            type: Boolean,
            default: false,
        },

        size: {
            type: String,
            default: 'md',
        },
    },

    data() {
        return {
            states,
            labels: {
                [states.HIDDEN]: 'Hidden',
                [states.SUBMITTING]: 'Submitting',
                [states.GRADING]: 'Grading',
                [states.OPEN]: 'Open',
                [states.DONE]: 'Done',
            },
            icons: {
                [states.HIDDEN]: 'eye-slash',
                [states.SUBMITTING]: 'clock-o',
                [states.GRADING]: 'pencil',
                [states.OPEN]: 'clock-o',
                [states.DONE]: 'check',
            },
            iconScale: 0.75,
        };
    },

    computed: {
        ltiHiddenOpenVariant() {
            const st = this.assignment.state;
            return st !== states.DONE ? 'primary' : 'outline-primary';
        },

        hiddenVariant() {
            const st = this.assignment.state;
            return st === states.HIDDEN ? 'danger' : 'outline-danger';
        },

        openVariant() {
            const st = this.assignment.state;
            return st === states.SUBMITTING || st === states.GRADING || st === states.OPEN
                ? 'warning'
                : 'outline-warning';
        },

        doneVariant() {
            const st = this.assignment.state;
            return st === states.DONE ? 'success' : 'outline-success';
        },

        canManageLTIState() {
            return this.assignment.is_lti
                && ltiProviders[this.assignment.lti_provider].supportsStateManagement;
        },
    },

    methods: {
        ...mapActions('courses', ['updateAssignment']),

        updateState(pendingState) {
            return this.$http
                .patch(`/api/v1/assignments/${this.assignment.id}`, {
                    state: pendingState,
                })
                .then(() => pendingState);
        },

        afterUpdateState(pendingState) {
            this.updateAssignment({
                assignmentId: this.assignment.id,
                assignmentProps: {
                    state: pendingState,
                },
            });
        },
    },

    components: {
        Icon,
        Loader,
        SubmitButton,
    },
};
</script>

<style lang="less" scoped>
.state-button.larger {
    width: 4em;

    .fa-icon {
        margin-left: 0;
    }
}
</style>
