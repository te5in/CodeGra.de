<template>
<div class="assignment-submit-types">
    <b-input-group class="d-flex">
        <b-input-group-prepend is-text>
            Allowed upload types

            <description-popover hug-text>
                Select how you want your student to hand in their
                submissions. You can either select a file uploader, via a
                GitHub/GitLab webhook, or both.
            </description-popover>
        </b-input-group-prepend>

        <b-input-group-prepend class="flex-grow-1">
            <b-input-group-text class="flex-grow-1 no-bg">
                <b-form-checkbox v-model="files">
                    File uploader

                    <description-popover hug-text>
                        Your students will be able to upload files via a file
                        uploader, they can submit archives which are
                        automatically extracted or regular files. If you setup
                        hand-in requirements, the handed in files will be
                        checked on these requirements.
                    </description-popover>
                </b-form-checkbox>
            </b-input-group-text>
        </b-input-group-prepend>

        <b-input-group-prepend class="flex-grow-1">
            <b-input-group-text class="flex-grow-1 no-bg">
                <b-form-checkbox v-model="webhook">
                    GitHub/GitLab

                    <description-popover hug-text>
                        Your students will be able to hand in via a GitHub or
                        GitLab webhook. Instructions on how to set this up will
                        be shown on the hand in page. Hand-in requirements will
                        be ignored on submissions handed in through this method.
                    </description-popover>
                </b-form-checkbox>
            </b-input-group-text>
        </b-input-group-prepend>

        <b-input-group-append>
            <submit-button :submit="submit" ref="submitButton"/>
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
    name: 'assignment-submit-types',

    props: {
        assignmentId: {
            type: Number,
            required: true,
        },
    },

    data() {
        return {
            files: true,
            webhook: true,
        };
    },

    watch: {
        assignmentId: {
            handler() {
                this.setRemoteData();
            },
            immediate: true,
        },
    },

    computed: {
        ...mapGetters('courses', ['assignments']),

        assignment() {
            return this.assignments[this.assignmentId];
        },
    },

    methods: {
        ...mapActions('courses', ['updateAssignment']),

        setRemoteData() {
            this.files = this.assignment.files_upload_enabled;
            this.webhook = this.assignment.webhook_upload_enabled;
        },

        submit() {
            const data = {
                files_upload_enabled: this.files,
                webhook_upload_enabled: this.webhook,
            };
            return this.$http
                .patch(`/api/v1/assignments/${this.assignment.id}`, data)
                .then(response => {
                    this.updateAssignment({
                        assignmentId: this.assignmentId,
                        assignmentProps: data,
                    });
                    return response;
                });
        },
    },

    components: {
        Icon,
        SubmitButton,
        DescriptionPopover,
    },
};
</script>

<style lang="less">
.flex-grow-1 {
    flex: 1 1 auto;
}
</style>
