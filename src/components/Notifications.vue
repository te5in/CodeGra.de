<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="notifications">
    <div>
        <b-form-checkbox v-model="graders">
            <b>Graders</b>
            <description-popover
                hug-text
                description="Toggle this checkbox to send a reminder to the
                             graders that are causing the grading to not be done
                             at the given time."
                placement="right"/>
        </b-form-checkbox>
        <b-collapse :visible="graders" :id="`collapse-${Math.random()}`">
            <b-input-group prepend="Time to send"
                           class="extra-box">
                <datetime-picker v-model="reminderTime"/>
            </b-input-group>
        </b-collapse>
    </div>
    <hr/>
    <div>
        <b-form-checkbox v-model="finished">
            <b>Finished</b>
            <description-popover
                hug-text
                description="Toggle this checkbox to send the given email
                             address a reminder when the grading is done. You
                             can select multiple address in the same as in your
                             email client."
                placement="right"/>
        </b-form-checkbox>
        <b-collapse :visible="finished" :id="`collapse-${Math.random()}`">
            <b-input-group prepend="Send to"
                           class="extra-box">
                <input type="text"
                       @keyup.ctrl.enter="$refs.updateReminder.onClick"
                       class="form-control"
                       v-model="doneEmail"/>
            </b-input-group>
        </b-collapse>
    </div>
    <hr/>
    <b-collapse :visible="graders || finished"
                class="grade-options"
                :id="`collapse-${Math.random()}`">
        <b-form-radio-group v-model="doneType">
            <b-form-radio v-for="item in options"
                          :key="item.value"
                          :value="item.value">
                {{ item.text }}
                <description-popover
                    :description="item.help"
                    hug-text
                    placement="right"/>
            </b-form-radio>
        </b-form-radio-group>
        <hr style="width: 100%"/>
    </b-collapse>

    <submit-button ref="updateReminder"
                   :submit="updateReminder" />
</div>
</template>

<script>
import { mapActions } from 'vuex';

import SubmitButton from './SubmitButton';
import DescriptionPopover from './DescriptionPopover';
import DatetimePicker from './DatetimePicker';

export default {
    props: {
        assignment: {
            type: Object,
            default: null,
        },
    },

    computed: {
        assignmentUrl() {
            return `/api/v1/assignments/${this.assignment.id}`;
        },
    },

    data() {
        return {
            graders: this.assignment.reminderTime.isValid(),
            reminderTime: this.$utils.formatDate(this.assignment.getReminderTimeOrDefault()),
            finished: this.assignment.done_email != null,
            doneEmail: this.assignment.done_email,
            doneType: this.assignment.done_type,
            options: [
                {
                    text: 'Assigned graders only',
                    value: 'assigned_only',
                    help: `
Only send to graders that have work assigned to them. This can be because they were
divided or because they were assigned work manually.`,
                },
                {
                    text: 'All graders',
                    value: 'all_graders',
                    help: 'Send a reminder e-mail to all graders.',
                },
            ],
        };
    },

    watch: {
        finished(val) {
            if (!val && !this.graders) {
                this.doneType = null;
            }
        },

        graders(val) {
            if (!val && !this.finished) {
                this.doneType = null;
            }
        },
    },

    methods: {
        ...mapActions('courses', ['updateAssignmentReminder']),

        updateReminder() {
            if ((this.graders || this.finished) && !this.doneType) {
                let msg =
                    'Please select when grading on this assignment should be considered finished.';
                if (this.graders) {
                    msg +=
                        ' This also indicates who should get a notification when they are not yet done grading.';
                }
                throw new Error(msg);
            }

            return this.updateAssignmentReminder({
                assignmentId: this.assignment.id,
                doneType: this.doneType,
                doneEmail: this.finished ? this.doneEmail : null,
                reminderTime: this.graders ? this.reminderTime : null,
            });
        },
    },

    components: {
        SubmitButton,
        DescriptionPopover,
        DatetimePicker,
    },
};
</script>

<style lang="less" scoped>
hr {
    margin-top: 0.5rem;
    margin-bottom: 0.5rem;
}

.grade-options {
    padding-left: 3px;

    & > .custom-control:last-child {
        margin-bottom: 0;
    }
}

label {
    margin-bottom: 0;
}

.extra-box {
    padding: 0.75em 0;
}

.submit-button {
    float: right;
}
</style>
