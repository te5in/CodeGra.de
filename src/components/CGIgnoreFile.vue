<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
    <div class="cgignore-file">
        <textarea class="form-control"
                  rows="6"
                  v-model="content"
                  @keyup.ctrl.enter.prevent="$refs.submitBtn.onClick"/>
        <submit-button label="Update"
                       ref="submitBtn"
                       :submit="updateIgnore"
                       @success="afterUpdateIgnore"/>
    </div>
</template>

<script>
import { mapGetters, mapActions } from 'vuex';

import SubmitButton from './SubmitButton';

export default {
    name: 'ignore-file',

    props: {
        assignmentId: {
            type: Number,
            required: true,
        },
    },

    computed: {
        ...mapGetters('courses', ['assignments']),

        assignment() {
            return this.assignments[this.assignmentId];
        },
    },

    data() {
        return {
            content: '',
        };
    },

    mounted() {
        this.content = this.assignment.cgignore || '';
    },

    methods: {
        ...mapActions('courses', ['updateAssignment']),

        updateIgnore() {
            const newContent = this.content;

            return this.$http
                .patch(`/api/v1/assignments/${this.assignment.id}`, {
                    ignore: newContent,
                })
                .then(() => newContent);
        },

        afterUpdateIgnore(newContent) {
            this.updateAssignment({
                assignmentId: this.assignmentId,
                assignmentProps: {
                    cgignore: newContent,
                },
            });
        },
    },

    components: {
        SubmitButton,
    },
};
</script>

<style lang="less" scoped>
.submit-button {
    float: right;
    margin-top: 1rem;
}
</style>
