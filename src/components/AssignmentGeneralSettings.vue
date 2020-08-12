<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<b-card v-if="permissions.canEditSomeGeneralSettings"
        header="General"
        class="assignment-general-settings">
    <b-form-group label-cols="6" label-class="py-0"
                  :id="`assignment-type-${uniqueId}`"
                  :label-for="`assignment-type-${uniqueId}-toggle`">
        <template #label>
            Assignment type

            <!-- TODO: Improve popover text -->
            <cg-description-popover hug-text>
                Bla die bla
            </cg-description-popover>
        </template>

        <cg-toggle
            class="float-right"
            :id="`assignment-type-${uniqueId}-toggle`"
            v-model="kind"
            label-off="Normal"
            label-on="Exam"
            :value-off="normalKind"
            :value-on="examKind" />
    </b-form-group>

    <!-- TODO: Improve description text -->
    <b-form-group
        label="Assignment name"
        :description="permissions.canEditName ? '' : 'You cannot change the name of an LTI assignment.'">
        <input type="text"
               class="form-control"
               v-model="name"
               :disabled="!permissions.canEditName"
               @keydown.ctrl.enter="$refs.submitGeneralSettings.onClick"/>
    </b-form-group>

    <b-form-group v-if="kind === examKind"
                  :id="`assignment-available-at-${uniqueId}`"
                  :label-for="`assignment-available-at-${uniqueId}-input`">
        <template #label>
            Available from

            <cg-description-popover hug-text>
                Bla die bla
            </cg-description-popover>
        </template>

        <b-input-group v-b-popover.top.hover="availableAtPopover"
                       append="hours before the deadline">
            <cg-number-input
                :id="`assignment-available-at-${uniqueId}-input`"
                :min="0"
                :step="1"
                :value="hoursToDeadline"
                @input="updateAvailableAt" />
        </b-input-group>
    </b-form-group>

    <b-form-group v-else
                  :id="`assignment-available-at-${uniqueId}`"
                  :label-for="`assignment-available-at-${uniqueId}-input`">
        <template #label>
            Available at

            <cg-description-popover hug-text>
                The time the assignment should switch from the
                hidden state to the open state. With the default
                permissions this means that students will be
                able to see the assignment at this moment.
            </cg-description-popover>
        </template>

        <b-input-group v-b-popover.top.hover="availableAtPopover">
            <datetime-picker v-model="availableAt"
                             :disabled="!permissions.canEditAvailableAt"
                             :id="`assignment-available-at-${uniqueId}-input`"
                             placeholder="Manual"/>

            <b-input-group-append
                v-if="permissions.canEditAvailableAt"
                v-b-popover.top.hover="availableAt == null ? '' : 'Revert to manual mode.'">

                <b-button
                    @click="availableAt = null"
                    :disabled="!permissions.canEditAvailableAt || availableAt == null"
                    variant="warning">
                    <fa-icon name="reply"/>
                </b-button>
            </b-input-group-append>
        </b-input-group>
    </b-form-group>

    <!-- TODO: Improve description text -->
    <b-form-group
        :state="assignment.hasDeadline"
        :description="permissions.canEditDeadline ? '' : 'You cannot change the deadline!'"
        :id="`assignment-deadline-${uniqueId}`"
        :label-for="`assignment-deadline-${uniqueId}-input`"
        invalid-feedback="The deadline has not been set yet!">
        <template #label>
            Deadline

            <cg-description-popover hug-text>
                <template v-if="assignment.ltiProvider.isJust()"
                          slot="description">
                    {{ lmsName.extract() }} did not pass this
                    assignment's deadline on to CodeGrade.
                    Students will not be able to submit their
                    work until the deadline is set here.
                </template>
                <template v-else
                          slot="description">
                    Students will not be able to submit work
                    unless a deadline has been set.
                </template>
            </cg-description-popover>
        </template>

        <datetime-picker
            v-model="deadline"
            :id="`assignment-deadline-${uniqueId}-input`"
            class="assignment-deadline"
            placeholder="None set"
            :disabled="!permissions.canEditDeadline"/>
    </b-form-group>

    <b-form-group v-if="permissions.canEditMaxGrade"
                  :id="`assignment-max-points-${uniqueId}`"
                  :label-for="`assignment-max-points-${uniqueId}-input`">
        <template #label>
            Max points

            <cg-description-popover hug-text>
                The maximum grade it is possible to achieve for
                this assignment.  Setting this value enables
                you to give 'bonus' points for an assignment,
                as a 10 will still be seen as a perfect score.
                So if this value is 12 a user can score
                2 additional bonus points. The default value is
                10. Existing grades will not be changed by
                changing this value!
            </cg-description-popover>
        </template>

        <b-input-group class="maximum-grade">
            <cg-number-input
                :min="0"
                :step="1"
                :id="`assignment-max-points-${uniqueId}-input`"
                placeholder="10"
                v-model="maxGrade" />

            <b-input-group-append
                v-b-popover.hover.top="maxGrade == null ? '' : 'Reset to the default value.'">
                <b-button
                    variant="warning"
                    @click="maxGrade = null"
                    :disabled="maxGrade == null">
                    <fa-icon name="reply"/>
                </b-button>
            </b-input-group-append>
        </b-input-group>
    </b-form-group>

    <div class="float-right"
         v-b-popover.top.hover="submitGeneralSettingsPopover">
        <cg-submit-button
            ref="submitGeneralSettings"
            :disabled="nothingChanged"
            :submit="submitGeneralSettings" />
    </div>
</b-card>
</template>

<script lang="ts">
import { Vue, Component, Prop, Watch } from 'vue-property-decorator';
import { mapActions } from 'vuex';
import { AxiosResponse } from 'axios';

import * as models from '@/models';

// @ts-ignore
import DatetimePicker from './DatetimePicker';

@Component({
    components: {
        DatetimePicker,
    },
    methods: {
        ...mapActions('courses', [
            'updateAssignmentGeneralSettings',
        ]),
    },
})
export default class AssignmentGeneralSettings extends Vue {
    @Prop({ required: true })
    assignment!: models.Assignment

    normalKind: models.AssignmentKind = models.AssignmentKind.normal;

    examKind: models.AssignmentKind = models.AssignmentKind.exam;

    name: string | null = null;

    kind: models.AssignmentKind = models.AssignmentKind.normal;

    availableAt: string | null = null;

    deadline: string | null = null;

    maxGrade: number | null = null;

    readonly uniqueId: number = this.$utils.getUniqueId();

    get hoursToDeadline() {
        const { deadline, availableAt } = this;

        if (deadline == null || availableAt == null) {
            return null;
        } else {
            return this.$utils.toMoment(deadline).diff(availableAt) / 1000 / 60 / 60;
        }
    }

    updateAssignmentGeneralSettings!:
        (args: any) => Promise<AxiosResponse<void>>;

    get assignmentId() {
        return this.assignment.id;
    }

    @Watch('assignmentId', { immediate: true })
    onAssignmentChanged() {
        this.name = this.assignment.name;
        this.kind = this.assignment.kind;
        this.availableAt = this.$utils.formatNullableDate(
            this.assignment.availableAt,
            true,
        );
        this.deadline = this.$utils.formatNullableDate(
            this.assignment.deadline,
            true,
        );
        this.maxGrade = this.assignment.max_grade;
    }

    get permissions() {
        return new models.AssignmentCapabilities(this.assignment);
    }

    get nothingChanged() {
        if (this.kind !== this.assignment.kind) {
            return false;
        }

        if (this.name !== this.assignment.name) {
            return false;
        }

        if (this.assignment.availableAt == null) {
            if (this.availableAt != null) {
                return false;
            }
        } else if (!this.assignment.availableAt.isSame(this.availableAt)) {
            return false;
        }

        if (this.assignment.deadline == null) {
            if (this.deadline != null) {
                return false;
            }
        } else if (!this.assignment.deadline.isSame(this.deadline)) {
            return false;
        }

        if (this.maxGrade !== this.assignment.max_grade) {
            return false;
        }

        return true;
    }

    get submitGeneralSettingsPopover() {
        if (this.nothingChanged) {
            return 'Nothing has changed.';
        } else {
            return '';
        }
    }

    get availableAtPopover() {
        const lmsName = this.assignment.ltiProvider.map(prov => prov.lms);

        if (this.permissions.canEditAvailableAt || lmsName.isNothing()) {
            return '';
        } else {
            return `The state is managed by ${lmsName.extract()}`;
        }
    }

    updateAvailableAt(hoursToDeadline: number | null) {
        if (this.deadline != null && hoursToDeadline != null) {
            this.availableAt = this.$utils.formatDate(
                this.$utils.toMoment(this.deadline).subtract(hoursToDeadline, 'hour'),
                true,
            );
        }
    }

    submitGeneralSettings() {
        return this.updateAssignmentGeneralSettings({
            assignmentId: this.assignment.id,
            rame: this.name,
            kind: this.kind,
            availableAt: this.availableAt,
            deadline: this.deadline,
            maximumGrade: this.maxGrade == null ? null : Number(this.maxGrade),
        });
    }
}
</script>
