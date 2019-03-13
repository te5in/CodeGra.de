<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="submission-uploader">
    <b-modal id="wrong-files-modal"
             v-if="showWrongFileModal"
             hide-footer
             title="Probably superfluous files found!">
        <p>
            The following files should not be in your archive according to
            the <code style="margin: 0 0.25rem;">.cgignore</code> file. This
            means the following files are probably not necessary to hand
            in:
        </p>
        <ul class="wrong-files-list">
            <li style="margin-right: 2px; padding: 0.5em;" v-for="file in wrongFiles">
                <code style="margin-right: 0.25rem">{{ file[0] }}</code> is ignored by <code>{{ file[1] }}</code>
            </li>
        </ul>
        <p>
            This could be a mistake so please make sure no necessary code is
            present in these files before you delete them!
        </p>
        <b-button-toolbar justify>
            <submit-button label="Delete files"
                           variant="danger"
                           :submit="() => overrideSubmit('delete')"
                           @after-success="afterOverrideSubmit"
                           @error="$emit('error', $event)"/>

            <submit-button label="Keep files"
                           variant="warning"
                           :submit="() => overrideSubmit('keep')"
                           @after-success="afterOverrideSubmit"
                           @error="$emit('error', $event)"/>

            <b-button variant="outline-primary"
                      @click="$root.$emit('bv::hide::modal', 'wrong-files-modal')">
                Cancel submission
            </b-button>
        </b-button-toolbar>
    </b-modal>

    <b-modal id="group-manage-modal"
             v-if="showGroupModal"
             hide-footer
             title="Group">
        <div class="group-modal-wrapper">
            <p class="header">
                This assignment is a group assignment. Each group should have at
                least {{ assignment.group_set.minimum_size }} members.

                <span v-if="currentGroup">
                    <span v-if="differentAuthor">{{ currentAuthor.name }} is</span>
                    <span v-else>You are</span>
                    currently member of a group with
                    {{ currentGroup.members.length }} members.
                </span>
                <span v-else>
                    <span v-if="differentAuthor">{{ currentAuthor.name }} is</span>
                    <span v-else>You are</span>
                    currently not member of any group.
                </span>
            </p>
            <p v-if="assignment.is_lti">
                This assignment is connected to an assignment in your
                {{ lmsName }}. This means that every user has to open the
                assignment at least once through {{ lmsName }}. Every user
                below <b>without</b> a check-mark next to their name should try
                to (re)open the assignment. If this issue persists, please
                contact CodeGrade support. You cannot submit while there are
                still members without a check-mark next to their name.
            </p>

            <div class="group-modal-body">
                <groups-management :assignment="assignment"
                                   :course="assignment.course"
                                   :group-set="assignment.group_set"
                                   :filter="currentGroup ? ((group) => currentGroup.id == group.id) : (() => true)"
                                   :show-lti-progress="currentGroup && assignment.is_lti ?
                                                       ((group) => currentGroup.id === group.id) :
                                                       (() => false)"
                                   @groups-changed="groupsChanged"
                                   :show-add-button="!currentGroup"/>
            </div>
        </div>

        <b-button-toolbar justify>
            <b-button variant="danger"
                      @click="$root.$emit('bv::hide::modal', 'group-manage-modal')">
                Cancel submission
            </b-button>

            <submit-button label="Try again"
                           :disabled="groupSubmitPossible"
                           :submit="trySubmitAgain"
                           @success="afterTrySubmitAgain"
                           @error="trySubmitAgainError"
                           />
        </b-button-toolbar>
    </b-modal>

    <file-uploader ref="uploader"
                   :button-id="uploaderId"
                   :url="getUploadUrl()"
                   :disabled="disabled"
                   :confirm="confirmationMessage"
                   @error="uploadError"
                   @clear="author = null"
                   @response="response"
                   :maybe-handle-error="handleUploadError">
        <user-selector v-model="author"
                       select-label=""
                       :disabled="disabled"
                       :base-url="`/api/v1/courses/${assignment.course.id}/users/`"
                       :use-selector="canListUsers"
                       v-if="forOthers"
                       :placeholder="`${defaultAuthor.name} (${defaultAuthor.username})`"/>
    </file-uploader>
</div>
</template>

<script>
import { mapGetters, mapActions } from 'vuex';

import Loader from './Loader';
import FileUploader from './FileUploader';
import SubmitButton from './SubmitButton';
import UserSelector from './UserSelector';
import GroupManagement from './GroupManagement';
import GroupsManagement from './GroupsManagement';

let i = 0;

export default {
    name: 'submission-uploader',

    props: {
        assignment: {
            required: true,
            type: Object,
        },

        disabled: {
            default: false,
            type: Boolean,
        },

        forOthers: {
            type: Boolean,
            required: true,
        },

        canListUsers: {
            type: Boolean,
            required: true,
        },
    },

    computed: {
        ...mapGetters('user', { myUsername: 'username', myName: 'name' }),

        defaultAuthor() {
            return { name: this.myName, username: this.myUsername };
        },

        groupSubmitPossible() {
            return (
                !this.currentGroup ||
                this.currentGroup.members.length < this.assignment.group_set.minimum_size
            );
        },

        differentAuthor() {
            return !!(this.forOthers && this.author);
        },

        currentAuthor() {
            return this.differentAuthor ? this.author : this.defaultAuthor;
        },

        confirmationMessage() {
            if (
                this.forOthers &&
                (this.author == null || this.defaultAuthor.username === this.author.username)
            ) {
                return 'You are now submitting with yourself as author, are you sure you want to continue?';
            } else {
                return '';
            }
        },

        lmsName() {
            return this.assignment.lms_name;
        },
    },

    data() {
        return {
            emptySet: new Set(),
            wrongFiles: [],
            author: null,
            // This variable is a haxxxy optimization: Rendering a modal is SLOW
            // (!!) as it forces an entire reflow even when it is still
            // hidden. I most cases the modal on this page is never shown (it is
            // only shown when a user tries to hand in files that match the
            // ignore filters), so by default we don't render it (there is a
            // `v-if="showWrongFileModal"`) at all. When the modal is needed we
            // set this variable to `true`. We never reset this value back to
            // `false` as doing so f*cks the entire animation.
            showWrongFileModal: false,
            showGroupModal: false,
            uploaderId: `submission-uploader-${i++}`,
            currentGroup: null,
        };
    },

    destroyed() {
        // Make sure we don't leak the promise and event handler
        // set in the checkUpload method.
        this.$emit('warn-popover-hidden');
    },

    methods: {
        ...mapActions('courses', ['addSubmission']),

        groupsChanged(newGroups) {
            for (let index = 0; index < newGroups.length; ++index) {
                const group = newGroups[index];
                const needle = this.currentAuthor.username;
                if (group.members.some(user => user.username === needle)) {
                    this.currentGroup = group;
                    return;
                }
            }
            this.currentGroup = null;
        },

        isArchiveError(err) {
            const { code } = err.response.data;
            return code === 'INVALID_FILE_IN_ARCHIVE';
        },

        isGroupError(err) {
            const { code } = err.response.data;
            return (
                code === 'INSUFFICIENT_GROUP_SIZE' || code === 'ASSIGNMENT_RESULT_GROUP_NOT_READY'
            );
        },

        handleUploadError(err) {
            return this.isArchiveError(err) || this.isGroupError(err);
        },

        async uploadError(err) {
            const { data } = err.response;

            if (this.isArchiveError(err)) {
                this.wrongFiles = data.invalid_files;
                this.showWrongFileModal = true;
                await this.$nextTick();
                this.$root.$emit('bv::show::modal', 'wrong-files-modal');
            } else if (this.isGroupError(err)) {
                this.currentGroup = data.group;
                this.showGroupModal = true;
                await this.$nextTick();
                this.$root.$emit('bv::show::modal', 'group-manage-modal');
            }
        },

        getUploadUrl(ignored = 'error') {
            let res = `/api/v1/assignments/${
                this.assignment.id
            }/submission?ignored_files=${ignored}`;
            if (this.differentAuthor) {
                res += `&author=${this.author.username}`;
            }
            return res;
        },

        overrideSubmit(type) {
            const { requestData } = this.$refs.uploader;
            const url = this.getUploadUrl(type);

            return this.$http.post(url, requestData);
        },

        afterOverrideSubmit(response) {
            const submission = response.data;

            this.addSubmission({
                assignmentId: this.assignment.id,
                submission,
            });
            this.$emit('created', submission);
            this.$root.$emit('bv::hide::modal', 'wrong-files-modal');
        },

        trySubmitAgain() {
            const { requestData } = this.$refs.uploader;
            const url = this.getUploadUrl();

            return this.$http.post(url, requestData);
        },

        afterTrySubmitAgain(response) {
            const submission = response.data;

            this.addSubmission({ assignmentId: this.assignment.id, submission });
            this.$emit('created', submission);
            this.$root.$emit('bv::hide::modal', 'wrong-files-modal');
            this.$root.$emit('bv::hide::modal', 'group-manage-modal');
        },

        trySubmitAgainError(response) {
            this.$emit('error', response);

            if (!this.isGroupError(response)) {
                this.uploadError(response);
            }
        },

        response({ data: submission }) {
            this.addSubmission({
                assignmentId: this.assignment.id,
                submission,
            });
            this.$emit('created', submission);
        },
    },

    components: {
        GroupManagement,
        GroupsManagement,
        FileUploader,
        SubmitButton,
        UserSelector,
        Loader,
    },
};
</script>

<style lang="less" scoped>
.form-group {
    margin-bottom: 0;
}

.wrong-files-list {
    flex: 1 1 auto;
    list-style: none;
    margin-right: -0.95rem;
    overflow: auto;
}

.group-modal-wrapper {
    overflow: auto;
    border-bottom: 1px solid #e9ecef;
    margin: -0.95rem;
    margin-bottom: 0.95rem;
    padding: 0.95rem;
    min-height: 50vh;
}

.group-modal-body .groups-management {
    margin: 5px 0;
}

.btn-toolbar {
    flex: 0 0 auto;
}
</style>

<style lang="less">
@import '~mixins.less';

.submission-uploader .multiselect {
    min-height: 0px;
    margin: 0 1px;
    .multiselect__tags {
        border-radius: 0;
        min-height: 0px;
    }
}

.submission-uploader {
    .modal-dialog {
        display: flex;
        flex-direction: column;
        height: auto;
        max-height: 75vh;
        min-width: 75vw;
        margin: 12.5vh auto;

        @media @media-small {
            max-height: ~'calc(100vh - 2rem)';
            margin: 1rem auto;
        }
    }

    .modal-content {
        min-height: 0;
    }

    .modal-body {
        display: flex;
        flex-direction: column;
        min-height: 0;
    }
}
</style>
