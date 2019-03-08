<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="notifications">
    <div>
        <b-form-checkbox v-model="graders">
            <b>Graders</b>
            <description-popover
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
            <description-popover placement="right">
                <template slot="description">
                    Toggle this checkbox to send a reminder to the given email
                    address when the grading is done. You can enter multiple email
                    addresses separated by ";".
                </template>
            </description-popover>
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
                   :submit="updateReminder"
                   @success="afterUpdateReminder"/>
</div>
</template>

<script>
import { mapActions } from 'vuex';
import moment from 'moment';

import { convertToUTC } from '@/utils';

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
            graders: this.assignment.has_reminder_time,
            reminderTime: this.assignment.reminder_time,
            finished: this.assignment.done_email != null,
            doneEmail: this.assignment.done_email,
            doneType: this.assignment.done_type,
            options: [
                {
                    text: 'Assigned graders only',
                    value: 'assigned_only',
                    help: `
Only send to graders that have submissions assigned (manually or automatically
divided) to them.`,
                },
                {
                    text: 'All graders',
                    value: 'all_graders',
                    help: 'Send a reminder email to all graders.',
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
        ...mapActions('courses', ['updateAssignment']),

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

            const props = {
                done_type: this.doneType,
                done_email: this.finished ? this.doneEmail : null,
                reminder_time: this.graders ? convertToUTC(this.reminderTime) : null,
            };

            return this.$http.patch(this.assignmentUrl, props);
        },

        afterUpdateReminder() {
            const time = this.graders ? convertToUTC(this.reminderTime) : null;
            const email = this.finished ? this.doneEmail : null;

            const props = {
                done_type: this.doneType,
                done_email: email,
                reminder_time: time,
            };

            if (this.graders || this.finished) {
                props.reminder_time = moment
                    .utc(time)
                    .local()
                    .format('YYYY-MM-DDTHH:mm');
            }

            this.updateAssignment({
                assignmentId: this.assignment.id,
                assignmentProps: props,
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
