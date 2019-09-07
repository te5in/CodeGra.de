<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="submission-uploader"
     :class="noBorder ? 'no-border' : ''">
    <b-modal id="wrong-files-modal"
             v-if="showWrongFileModal"
             hide-footer
             title="Your submission does not follow the hand-in instruction required by your teacher!">
        <div v-if="oldIgnoreFormat">
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
        </div>
        <div v-else class="wrong-files-modal-content">
            <b-tabs no-fade class="missing-required-files-tabs"
                    content-class="missing-required-files-content">
                <b-tab title="Missing files" class="ignore-tab" :disabled="wrongFileError.missing_files.length === 0">
                    <b-card class="ignore-card missing-card" no-body>
                        <p class="explanation">
                            The following files were required by your teacher, but
                            were not found in your submission.
                        </p>
                        <ul class="striped-list">
                            <li v-for="missing in wrongFileError.missing_files"
                                :key="missing.name">
                                <file-rule :value="missing"
                                           policy=""
                                           :editable="false"
                                           :all-rules="[]"
                                           :editing="false"
                                           hide-rule-type/>
                            </li>
                        </ul>
                    </b-card>
                </b-tab>
                <b-tab title="Denied files" class="ignore-tab"
                       :disabled="wrongFileError.removed_files.every(x => x.deletion_type === 'leading_directory')">
                    <b-card class="ignore-card p-2" no-body>
                        <file-tree-inner :tree="deheadedFileTree"
                                         :collapsed="false"
                                         :collapse-function="expandFileTree"
                                         no-links>
                            <template slot="file-slot"
                                      slot-scope="f">
                                <span class="deleted-file"
                                      v-b-popover.hover.top.window="'This file is denied.'"
                                      v-if="fileDeletionRule(f.fullFilename)"
                                      >{{ f.filename }}</span>
                                <span class="not-denied-file" v-else>{{ f.filename }}</span>
                            </template>
                            <template slot="dir-slot"
                                      slot-scope="f">
                                <span class="deleted-file"
                                      v-if="fileDeletionRule(f.fullFilename)"
                                      v-b-popover.top.hover.window="'This directory and all its files are denied.'"
                                      >{{ f.filename }}</span>
                                <span v-else-if="f.depth > 1 && dirContainsDeletions(f.fullFilename)"
                                      v-b-popover.top.hover.window="'This directory contains files which are denied.'"
                                      class="dir-with-deletions"
                                      >{{ f.filename }}</span>
                                <span :class="f.depth > 1 ? 'not-denied-file' : ''" v-else>{{ f.filename }}</span>
                            </template>
                        </file-tree-inner>
                    </b-card>
                </b-tab>
                <b-tab title="Hand-in instructions" class="ignore-tab">
                    <b-card class="ignore-card" no-body>
                        <c-g-ignore-file :assignment-id="assignment.id"
                                         summary-mode
                                         :editable="false"/>
                    </b-card>
                </b-tab>
            </b-tabs>
        </div>
        <b-button-toolbar justify>
            <div v-b-popover.top.hover="canDeleteFiles ? '' : 'You are missing required files.'">
                <submit-button label="Delete disallowed files and hand in"
                               variant="danger"
                               :submit="() => overrideSubmit('delete')"
                               :disabled="!canDeleteFiles"
                               @after-success="afterOverrideSubmit"
                               @error="$emit('error', $event)"/>
            </div>

            <div v-b-popover.top.hover="canOverrideIgnore ? '' : (canDeleteFiles ? 'You are not allowed to override the hand-in requirements.' : 'You are missing required files.')">
                <submit-button label="Hand in anyway"
                               variant="warning"
                               :submit="() => overrideSubmit('keep')"
                               :disabled="!canOverrideIgnore"
                               @after-success="afterOverrideSubmit"
                               @error="$emit('error', $event)"/>
            </div>

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

    <multiple-files-uploader
        :no-border="noBorder"
        v-model="files" />

    <b-input-group>
        <template v-if="forOthers">
            <div class="author-wrapper"
                 v-b-popover.hover.top="authorDisabledPopover">
                    <user-selector v-if="forOthers"
                                   v-model="author"
                                   select-label=""
                                   :disabled="disabled || isTestSubmission"
                                   :base-url="`/api/v1/courses/${assignment.course.id}/users/`"
                                   :use-selector="canListUsers"
                                   :placeholder="`${defaultAuthor.name} (${defaultAuthor.username})`" />
            </div>

            <b-input-group-prepend is-text
                                   class="test-student-checkbox"
                                   v-b-popover.hover.top="testSubmissionDisabledPopover">
                <b-form-checkbox v-model="isTestSubmission"
                                 :disabled="disabled || author">
                    Test submission
                    <description-popover hug-text>
                        This submission will be uploaded by a special test student.
                        When you enable this option you will not be able to select
                        another author.
                    </description-popover>
                </b-form-checkbox>
            </b-input-group-prepend>
        </template>

        <b-input-group-prepend v-else
                               is-text
                               class="deadline-information">
            The assignment is due {{ readableDeadline }}.
        </b-input-group-prepend>

        <submit-button class="submit-file-button"
                       :disabled="disabled || files.length === 0"
                       :confirm="confirmationMessage"
                       :submit="uploadFiles"
                       :filter-error="handleUploadError"
                       @success="afterUploadFiles"/>
    </b-input-group>
</div>
</template>

<script>
import { mapGetters, mapActions } from 'vuex';
import moment from 'moment';

import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/times';

import Loader from './Loader';
import SubmitButton, { SubmitButtonCancelled } from './SubmitButton';
import UserSelector from './UserSelector';
import GroupManagement from './GroupManagement';
import GroupsManagement from './GroupsManagement';
import FileRule from './FileRule';
import CGIgnoreFile from './CGIgnoreFile';
import FileTreeInner from './FileTreeInner';
import MultipleFilesUploader from './MultipleFilesUploader';
import DescriptionPopover from './DescriptionPopover';

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

        noBorder: {
            type: Boolean,
            default: false,
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
                !this.isTestSubmission &&
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

        oldIgnoreFormat() {
            return (
                this.assignment.cgignore_version == null ||
                this.assignment.cgignore_version !== 'SubmissionValidator'
            );
        },

        canDeleteFiles() {
            return this.oldIgnoreFormat || this.wrongFileError.missing_files.length === 0;
        },

        canOverrideIgnore() {
            return (
                this.oldIgnoreFormat ||
                (this.wrongFileError.missing_files.length === 0 &&
                    this.assignment.cgignore.options.some(
                        opt => opt.key === 'allow_override' && opt.value,
                    ))
            );
        },

        deheadedFileTree() {
            if (this.oldIgnoreFormat || !this.wrongFileError) {
                return {};
            } else if (
                this.wrongFileError.removed_files.length === 0 ||
                this.wrongFileError.removed_files[0].deletion_type !== 'leading_directory'
            ) {
                return this.wrongFileError.original_tree;
            } else {
                const tree = this.wrongFileError.original_tree;
                while (tree.entries.length === 1 && tree.entries[0].entries != null) {
                    tree.entries = tree.entries[0].entries;
                }
                return tree;
            }
        },

        uploadUrl() {
            let res = `/api/v1/assignments/${this.assignment.id}/submission?ignored_files=${
                this.ignored
            }`;
            if (this.isTestSubmission) {
                res += '&is_test_submission';
            } else if (this.differentAuthor) {
                res += `&author=${this.author.username}`;
            }
            return res;
        },

        readableDeadline() {
            return moment(this.assignment.deadline).from(this.$root.$now);
        },

        authorDisabledPopover() {
            return this.disabled || this.isTestSubmission
                ? 'You cannot select both an author and upload as a test submission.'
                : '';
        },

        testSubmissionDisabledPopover() {
            return this.disabled || this.author
                ? 'You cannot select both an author and upload as a test submission.'
                : '';
        },
    },

    data() {
        return {
            wrongFiles: [],
            wrongFileError: null,
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
            ignored: 'error',
            currentGroup: null,
            ruleCache: {},
            files: [],
            isTestSubmission: false,
        };
    },

    watch: {
        wrongFileError() {
            this.ruleCache = {};
        },
    },

    destroyed() {
        // Make sure we don't leak the promise and event handler
        // set in the checkUpload method.
        this.$emit('warn-popover-hidden');
    },

    methods: {
        ...mapActions('submissions', ['addSubmission']),

        getRequestData() {
            const data = new FormData();
            this.files.forEach((f, i) => {
                data.append(`file${i}`, f);
            });
            return data;
        },

        expandFileTree(f) {
            return !(this.dirContainsDeletions(f) && !this.fileDeletionRule(f));
        },

        dirContainsDeletions(f) {
            const name = f.slice(this.deheadedFileTree.name.length + 2, f.length);
            // Extra slash to make sure we don't have name clashes in the cache.
            return this.fileDeletionRule(`${f}//`, other => other.startsWith(name));
        },

        fileDeletionRule(f, equals = (deletedFile, self) => deletedFile === self) {
            const name = f.slice(this.deheadedFileTree.name.length + 2, f.length);
            if (this.ruleCache[name] === undefined) {
                this.ruleCache[name] = null;
                for (let i = 0; i < this.wrongFileError.removed_files.length; ++i) {
                    const removed = this.wrongFileError.removed_files[i];
                    if (
                        removed.deletion_type !== 'leading_directory' &&
                        equals(removed.fullname, name)
                    ) {
                        this.ruleCache[name] = removed;
                    }
                }
            }

            return this.ruleCache[name];
        },

        uploadFiles() {
            return this.$http.post(this.uploadUrl, this.getRequestData());
        },

        afterUploadFiles({ data: submission }) {
            this.files = [];
            this.addSubmission({
                assignmentId: this.assignment.id,
                submission,
            });
            this.$emit('created', submission);
        },

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
            if (this.isArchiveError(err) || this.isGroupError(err)) {
                this.uploadError(err);
                throw SubmitButtonCancelled;
            } else {
                throw err;
            }
        },

        async uploadError(err) {
            const { data } = err.response;
            this.ruleCache = {};

            if (this.isArchiveError(err)) {
                this.wrongFiles = data.invalid_files;
                this.wrongFileError = data;
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

        overrideSubmit(type) {
            this.ignored = type;
            return this.uploadFiles();
        },

        afterOverrideSubmit(response) {
            this.ignored = 'error';
            this.afterUploadFiles(response);
            this.$root.$emit('bv::hide::modal', 'wrong-files-modal');
        },

        trySubmitAgain() {
            return this.uploadFiles();
        },

        afterTrySubmitAgain(response) {
            this.afterUploadFiles(response);
            this.$root.$emit('bv::hide::modal', 'wrong-files-modal');
            this.$root.$emit('bv::hide::modal', 'group-manage-modal');
        },

        trySubmitAgainError(response) {
            this.$emit('error', response);

            if (!this.isGroupError(response)) {
                this.uploadError(response);
            }
        },
    },

    components: {
        GroupManagement,
        GroupsManagement,
        SubmitButton,
        UserSelector,
        FileRule,
        Loader,
        CGIgnoreFile,
        FileTreeInner,
        Icon,
        MultipleFilesUploader,
        DescriptionPopover,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

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

    #app.dark & {
        border-color: @color-primary-darker;
    }
}

.group-modal-body .groups-management {
    margin: 5px 0;
}

.btn-toolbar {
    flex: 0 0 auto;
}

.missing-card .explanation {
    padding: 0 0.75rem;
}

.ignore-card {
    padding-top: 0.75rem;
    border-top-right-radius: 0;
    border-top-left-radius: 0;
    border-top: 0;
    overflow-y: auto;
}

.ignore-tab {
    display: flex;
    flex-direction: column;
    min-height: 0;
    height: 100%;
}

.missing-required-files-tabs {
    display: flex;
    flex-direction: column;
    min-height: 0;
}

.wrong-files-modal-content {
    overflow-y: hidden;
    display: flex;
    flex-direction: column;
    margin-bottom: 1rem;
}

.deleted-file {
    color: @color-diff-removed-dark;
    text-decoration: underline wavy;
}

.dir-with-deletions {
    text-decoration: underline wavy @color-diff-removed-dark;
}

.not-denied-file {
    opacity: 0.6;
}

.submit-file-button {
    border-top-left-radius: 0;
    border-top-right-radius: 0;
    border-bottom-left-radius: 0;
}

.author-wrapper {
    flex: 1 1 auto;
}
</style>

<style lang="less">
@import '~mixins.less';

.submission-uploader {
    &.no-border .user-selector .multiselect__tags {
        border-bottom: none;
        border-left: none;
    }

    .deadline-information {
        flex: 1 1 auto;

        .input-group-text {
            width: 100%;
            background-color: transparent !important;

            #app.dark & {
                color: @text-color-dark !important;
            }
        }
    }

    .deadline-information .input-group-text,
    .test-student-checkbox .input-group-text,
    .multiselect .multiselect__tags {
        border-top-left-radius: 0;
        border-top-right-radius: 0;
    }

    #group-manage-modal .modal-dialog {
        max-width: 768px;
    }

    #wrong-files-modal .modal-dialog {
        display: flex;
        flex-direction: column;
        height: auto;
        max-height: 75vh;
        min-width: 75vw;
        margin: 12.5vh auto;
        max-width: 768px;

        @media @media-small {
            max-height: ~'calc(100vh - 2rem)';
            margin: 1rem auto;
        }

        .missing-required-files-content {
            min-height: 0;
            display: flex;
            flex-direction: column;
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
