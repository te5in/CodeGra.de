<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="maximum-grade">
    <b-input-group>
        <b-input-group-prepend is-text>
            Max points<description-popover
                          placement="top"
                          description="The maximum grade it is possible to
                                       achieve for this assignment.  Setting
                                       this value enables you to give 'bonus'
                                       points for an assignment, as a 10 will
                                       still be seen as a perfect score. So if
                                       this value is 12 a user can score 2
                                       additional bonus points. The default
                                       value is 10. Existing grades will not be
                                       changed by changing this value!"/>
        </b-input-group-prepend>
        <input type="number"
               min="0"
               step="1"
               v-model.number="maxGrade"
               @keydown.ctrl.enter="submit($refs.submitButton)"
               class="form-control"
               placeholder="10"/>
        <b-input-group-append>
            <submit-button @click="reset"
                           ref="resetButton"
                           :disabled="maxGrade == null"
                           v-b-popover.top.hover="maxGrade == null ? '' : 'Reset to the default value.'"
                           :label="false"
                           default="warning">
                <icon name="reply"/>
            </submit-button>
        </b-input-group-append>
        <b-input-group-append>
            <submit-button @click="submit($refs.submitButton)"
                           ref="submitButton"/>
        </b-input-group-append>
    </b-input-group>
</div>
</template>

<script>
import Icon from 'vue-awesome/components/Icon';
import { mapGetters, mapActions } from 'vuex';
import 'vue-awesome/icons/reply';

import SubmitButton from './SubmitButton';
import DescriptionPopover from './DescriptionPopover';

export default {
    name: 'maximum-grade',

    props: {
        assignmentId: {
            type: Number,
            required: true,
        },
    },

    data() {
        return {
            maxGrade: null,
        };
    },

    mounted() {
        this.maxGrade = this.assignment.max_grade;
    },

    computed: {
        ...mapGetters('courses', ['assignments']),

        assignment() {
            return this.assignments[this.assignmentId];
        },
    },

    methods: {
        ...mapActions('courses', ['updateAssignment']),

        reset() {
            this.maxGrade = null;
            this.submit(this.$refs.resetButton);
        },

        submit(btn = null) {
            const maxGrade =
                this.maxGrade === '' || this.maxGrade == null ? null : Number(this.maxGrade);

            const req = this.$http
                .patch(`/api/v1/assignments/${this.assignment.id}`, {
                    max_grade: maxGrade,
                })
                .then(
                    () => {
                        this.maxGrade = maxGrade;
                        this.updateAssignment({
                            assignmentId: this.assignmentId,
                            assignmentProps: {
                                max_grade: this.maxGrade,
                            },
                        });
                    },
                    ({ response }) => {
                        throw response.data.message;
                    },
                );
            return btn.submit(req);
        },
    },

    components: {
        Icon,
        SubmitButton,
        DescriptionPopover,
    },
};
</script>
