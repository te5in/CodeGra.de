<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="submission-uploader d-flex flex-column"
     :class="noBorder ? '' : 'border rounded'">
    <b-modal id="git-instructions-modal"
             v-if="gitData != null"
             title="Git instructions"
             hide-footer
             size="xl">
        <webhook-instructions :data="gitData" />
    </b-modal>

    <b-modal v-if="showWrongFileModal"
             id="wrong-files-modal"
             title="Your submission does not follow the hand-in instruction required by your teacher!"
             hide-footer
             size="xl">
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
                        <p class="m-3">
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
             title="Group"
             size="lg">
        <div class="group-modal-wrapper border-bottom">
            <p class="header">
                This assignment is a group assignment. Each group should have at
                least {{ assignment.group_set.minimum_size }} members.

                <span v-if="currentGroup != null">
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
                                   :filter="filterGroups"
                                   :show-lti-progress="currentGroup && assignment.is_lti ?
                                                       ((group) => currentGroup.id === group.id) :
                                                       (() => false)"
                                   :show-add-button="currentGroup == null"/>
            </div>
        </div>

        <b-button-toolbar justify>
            <b-button variant="danger"
                      @click="$root.$emit('bv::hide::modal', 'group-manage-modal')">
                Cancel submission
            </b-button>

            <submit-button label="Try again"
                           :disabled="groupSubmitNotPossible"
                           :submit="trySubmitAgain"
                           @success="afterTrySubmitAgain"
                           @error="trySubmitAgainError"
                           />
        </b-button-toolbar>
    </b-modal>

    <div v-if="maybeShowGitInstructions && assignment.webhook_upload_enabled"
         class="border-bottom text-center p-3">
        <span class="position-relative">
            <a href="#" @click.prevent="doGitSubmission" class="inline-link git-link">
                <u>
                    <b>
                        Click here for instructions on setting up Git
                        submissions<template v-if="isTestSubmission">
                            as the test student.
                        </template><template v-else-if="author != null">
                            as {{ author.name || author.username }}.
                        </template>
                        <template v-else>.</template>
                    </b>
                </u>
            </a>

            <span class="position-absolute pl-2" style="left: 100%;">
                <loader :scale="1" :center="false" v-if="loadingWebhookData"/>
                <icon v-show="loadingWebhookError != null"
                      name="times"
                      class="text-danger"
                      id="git-error-icon">
                </icon>
                <b-popover :show="loadingWebhookError != null"
                           target="git-error-icon"
                           triggers="blur"
                           placement="top"
                           @hide="loadingWebhookError = null"
                           @shown="$refs.loadingWebhookError.focus()">
                    <icon name="times"
                          class="hide-button"
                          @click.native="loadingWebhookError = null"/>
                    <span tabindex="-1"
                          ref="loadingWebhookError"
                          style="outline: 0;">
                        {{ $utils.getErrorMessage(loadingWebhookError) }}
                    </span>
                </b-popover>
            </span>
        </span>
    </div>

    <multiple-files-uploader
        no-border
        v-if="assignment.files_upload_enabled"
        v-model="files"
        class="flex-grow-1" />
    <div v-else
         class="bg-light p-3">
        Uploading submissions through files is disabled for this assignment. You
        can only hand-in submissions using git.
        <a href="#"
           @click.prevent="doGitSubmission"
           class="inline-link underline">Click here</a> for instructions on
           setting up Git submissions.
    </div>

    <b-input-group class="submit-options border-top" style="z-index: 25">
        <template v-if="forOthers">
            <div class="author-wrapper"
                 :class="canListUsers ? '' : 'd-flex'"
                 v-b-popover.hover.top="authorDisabledPopover">
                <user-selector v-if="forOthers"
                               v-model="author"
                               select-label=""
                               :disabled="disabled || isTestSubmission"
                               :base-url="`/api/v1/courses/${assignment.course.id}/users/`"
                               :use-selector="canListUsers"
                               :placeholder="`${loggedInUser.name} (${loggedInUser.username})`"
                               no-border />
            </div>

            <b-input-group-prepend class="test-student-checkbox border-left"
                                   :class="{ 'cursor-not-allowed': disabled || !!author }"
                                   v-b-popover.hover.top="testSubmissionDisabledPopover">
                <b-input-group-text class="border-0">
                    <b-form-checkbox v-model="isTestSubmission"
                                     :disabled="disabled || !!author">
                        Test submission
                        <description-popover hug-text placement="top">
                            This submission will be uploaded by a special test student.
                            When you enable this option you will not be able to select
                            another author.
                        </description-popover>
                    </b-form-checkbox>
                </b-input-group-text>
            </b-input-group-prepend>
        </template>

        <b-input-group-prepend v-else
                               class="deadline-information">
            <b-input-group-text class="border-0" v-if="assignment.hasDeadline">
                <span>
                    The assignment is due
                    <cg-relative-time :date="assignment.deadline" />
                </span>
            </b-input-group-text>
        </b-input-group-prepend>

        <submit-button class="submit-file-button"
                       :disabled="disabled || files.length === 0"
                       v-if="assignment.files_upload_enabled"
                       :confirm="confirmationMessage"
                       :submit="uploadFiles"
                       :class="showSubmissionLimiting ? 'rounded-0' : ''"
                       :filter-error="handleUploadError"
                       @success="afterUploadFiles"/>
    </b-input-group>

    <div v-if="showSubmissionLimiting" class="submission-limiting border-top p-2">
        <loader :scale="1" v-if="loadingUserSubmissions || loadingGroups" />
        <template v-else>
            <template v-if="currentResultingAuthorId === myId">
                You have
            </template>
            <template v-else>
                <user :user="currentResultingAuthor"
                      :before-group="loggedInUserIsInCurrentGroup ? 'Your group' :  'The group'"
                      /> has
            </template>
            <template v-if="amountSubmissionsLeft !== Infinity">
                <b>{{ amountSubmissionsLeft }}</b>
                {{ amountSubmissionsLeft === 1 ? 'submission' : 'submissions' }}
                left out of <b>{{ maxSubmissions }}</b>.
            </template>
            <template v-else>
                {{ submissionsByResultingAuthor.length }}
                {{ submissionsByResultingAuthor.length === 1 ? 'submission' : 'submissions'}}.
            </template>
            <span v-if="amountSubmissionsLeft !== 0 && coolOffPeriodText" v-html="coolOffPeriodText" />
        </template>
    </div>
</div>
</template>

<script>
import { mapGetters, mapActions } from 'vuex';
import moment from 'moment';
import * as utils from '@/utils';

import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/times';

import Loader from './Loader';
import SubmitButton, { SubmitButtonCancelled } from './SubmitButton';
import UserSelector from './UserSelector';
import User from './User';
import GroupManagement from './GroupManagement';
import GroupsManagement from './GroupsManagement';
import FileRule from './FileRule';
import CGIgnoreFile from './CGIgnoreFile';
import FileTreeInner from './FileTreeInner';
import MultipleFilesUploader from './MultipleFilesUploader';
import DescriptionPopover from './DescriptionPopover';
import WebhookInstructions from './WebhookInstructions';

// We export this function so that we can unit test it.
// Note that the `subs` parameter should be a list of submissions sorted by
// created date, ascending.
// This conflicts with prettier-eslint, so just ignore it for now
// eslint-disable-next-line object-curly-newline
export function getCoolOffPeriodText({ subs, author, loggedInUser, period, amountInPeriod, now }) {
    const escape = utils.htmlEscape;
    const bold = txt => `<b>${escape(txt)}</b>`;
    const numberToTimes = (n, inBold = true) => (inBold ? bold : escape)(utils.numberToTimes(n));

    let authorName;
    let authorPossess;
    let capitalize = utils.capitalize;

    if (loggedInUser.id === author.id) {
        authorName = 'you';
        authorPossess = 'your';
    } else if (author.isGroup && loggedInUser.isMemberOf(author.group)) {
        authorName = 'your group';
        authorPossess = "your group's";
    } else if (author.isGroup) {
        authorName = 'the group';
        authorPossess = "the group's";
    } else {
        authorName = escape(author.readableName);
        authorPossess = `${authorName}'s`;
        capitalize = x => x;
    }

    const humanizedPeriod = period.humanize().replace(/^a /, '');
    const cutoff = now.clone().subtract(period);
    const lines = [
        `You may submit <b>${numberToTimes(amountInPeriod, false)} every ${escape(
            humanizedPeriod,
        )}</b>.`,
    ];
    if (subs.length < amountInPeriod) {
        return lines[0];
    }
    lines.push(' ');

    const latestSubmissionDate = subs[subs.length - amountInPeriod].createdAt;
    const diff = moment.duration(latestSubmissionDate.diff(now));
    const waitTime = moment.duration(cutoff.diff(latestSubmissionDate));

    if (amountInPeriod === 1) {
        lines.push(
            `${capitalize(authorPossess)} latest submission was ${escape(diff.humanize(true))}`,
        );
    } else {
        lines.push(
            `${capitalize(authorName)} submitted ${numberToTimes(
                amountInPeriod,
                false,
            )} in the past ${escape(diff.humanize().replace(/^a /, ''))}`,
        );
    }
    if (latestSubmissionDate.isAfter(cutoff)) {
        let must;
        if (loggedInUser.id === author.id) {
            must = 'you must';
        } else {
            must = 'must';
        }
        lines.push(`, therefore ${must} wait for ${bold(waitTime.humanize())}.`);
    } else {
        lines.push('.');
    }
    return lines.join('');
}

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
        maybeShowGitInstructions: {
            type: Boolean,
            default: false,
        },
    },

    computed: {
        ...mapGetters('user', { myId: 'id' }),
        ...mapGetters('users', ['getGroupInGroupSetOfUser', 'getUser']),
        ...mapGetters('submissions', ['getSubmissionsByUser']),

        loggedInUser() {
            return this.getUser(this.myId);
        },

        loggedInUserIsInCurrentGroup() {
            return this.loggedInUser.isMemberOf(this.currentGroup);
        },

        groupSubmitNotPossible() {
            return !(
                this.currentGroup != null &&
                this.currentGroup.members.length >= this.assignment.group_set.minimum_size
            );
        },

        differentAuthor() {
            return !!(this.forOthers && this.author);
        },

        currentAuthor() {
            return this.differentAuthor ? this.author : this.loggedInUser;
        },

        groupSetId() {
            return this.$utils.getProps(this.assignment, null, 'group_set', 'id');
        },

        currentResultingAuthor() {
            const virtUser = this.getGroupInGroupSetOfUser(
                this.groupSetId,
                this.$utils.getProps(this.currentAuthor, null, 'id'),
            );
            return virtUser || this.currentAuthor;
        },

        currentResultingAuthorId() {
            return this.$utils.getProps(this.currentResultingAuthor, null, 'id');
        },

        confirmationMessage() {
            if (
                this.forOthers &&
                !this.isTestSubmission &&
                (this.author == null || this.loggedInUser.username === this.author.username)
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

        uploadUrlQueryArgs() {
            if (this.isTestSubmission) {
                return 'is_test_submission';
            } else if (this.differentAuthor) {
                return `author=${this.author.username}`;
            }
            return '';
        },

        uploadUrl() {
            return `/api/v1/assignments/${this.assignment.id}/submission?ignored_files=${
                this.ignored
            }&${this.uploadUrlQueryArgs}`;
        },

        disabledPopover() {
            return 'You cannot select both an author and upload as a test submission.';
        },

        authorDisabledPopover() {
            return this.disabled || this.isTestSubmission ? this.disabledPopover : '';
        },

        testSubmissionDisabledPopover() {
            return this.disabled || this.author ? this.disabledPopover : '';
        },

        currentGroup() {
            if (this.currentResultingAuthor && this.currentResultingAuthor.isGroup) {
                return this.currentResultingAuthor.group;
            }
            return null;
        },

        maxSubmissions() {
            return this.assignment.max_submissions;
        },

        coolOffPeriod() {
            return this.assignment.coolOffPeriod;
        },

        showSubmissionLimiting() {
            if (this.isTestSubmission || this.currentResultingAuthorId == null) {
                return false;
            }
            return this.maxSubmissions != null || this.coolOffPeriod.asMilliseconds() > 0;
        },

        coolOffPeriodText() {
            if (
                !this.showSubmissionLimiting ||
                this.coolOffPeriod.asMilliseconds() === 0 ||
                this.loadingUserSubmissions ||
                this.currentResultingAuthor == null
            ) {
                return '';
            }
            return getCoolOffPeriodText({
                subs: this.submissionsByResultingAuthor,
                author: this.currentResultingAuthor,
                loggedInUser: this.loggedInUser,
                period: this.coolOffPeriod,
                amountInPeriod: this.assignment.amount_in_cool_off_period,
                now: this.$root.$now,
            });
        },

        amountSubmissionsLeft() {
            const max = this.maxSubmissions;
            if (!this.showSubmissionLimiting || max == null) {
                return Infinity;
            }
            return Math.max(0, max - this.submissionsByResultingAuthor.length);
        },

        submissionsByResultingAuthor() {
            const author = this.currentResultingAuthor;
            if (author.id == null) {
                return [];
            }

            return this.getSubmissionsByUser(this.assignment.id, author.id);
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
            ruleCache: {},
            files: [],
            isTestSubmission: false,

            gitData: null,
            loadingWebhookData: false,
            loadingWebhookError: null,

            loadingUserSubmissions: false,
            loadingGroups: true,
        };
    },

    watch: {
        wrongFileError() {
            this.ruleCache = {};
        },

        coolOffPeriod() {
            this.loadSubmissionsIfNeeded();
        },

        maxSubmissions() {
            this.loadSubmissionsIfNeeded();
        },

        currentResultingAuthorId() {
            this.loadSubmissionsIfNeeded();
        },

        groupSetId: {
            immediate: true,
            handler(newValue) {
                if (newValue) {
                    this.loadingGroups = true;
                    this.loadGroupsOfGroupSet({
                        groupSetId: newValue,
                    }).then(() => {
                        if (this.groupSetId === newValue) {
                            this.loadingGroups = false;
                        }
                    });
                } else {
                    this.loadingGroups = false;
                }
            },
        },
    },

    mounted() {
        this.loadSubmissionsIfNeeded();
    },

    methods: {
        ...mapActions('submissions', ['addSubmission', 'loadSubmissionsByUser']),
        ...mapActions('users', ['addOrUpdateUser', 'loadGroupsOfGroupSet']),

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
            this.$root.$emit('cg::root::update-now');
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
                if (data.group) {
                    this.addOrUpdateUser({ user: data.group });
                }
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

        doGitSubmission() {
            this.loadingWebhookData = true;
            this.loadingWebhookError = null;
            const req = this.$http.post(
                `/api/v1/assignments/${this.assignment.id}/webhook_settings?webhook_type=git&${
                    this.uploadUrlQueryArgs
                }`,
            );

            return this.$utils.waitAtLeast(250, req).then(
                async ({ data }) => {
                    this.gitData = data;
                    this.loadingWebhookData = false;
                    await this.$afterRerender();
                    this.$root.$emit('bv::show::modal', 'git-instructions-modal');
                },
                err => {
                    this.loadingWebhookData = false;
                    this.loadingWebhookError = err;
                },
            );
        },

        filterGroups(group) {
            if (this.currentGroup) {
                return group.id === this.currentGroup.id;
            }
            return true;
        },

        loadSubmissionsIfNeeded() {
            if (!this.showSubmissionLimiting) {
                return;
            }

            this.loadingUserSubmissions = true;
            const authorId = this.currentResultingAuthorId;

            this.loadSubmissionsByUser({
                assignmentId: this.assignment.id,
                userId: authorId,
                force: false,
            }).then(() => {
                if (authorId === this.currentResultingAuthorId) {
                    this.loadingUserSubmissions = false;
                }
            });
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
        WebhookInstructions,
        User,
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

.ignore-card {
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

.submit-options div:last-child {
    border-top-right-radius: 0;
    .input-group-text {
        border-top-right-radius: 0;
    }
}

.submit-button.submit-file-button {
    border-top-left-radius: 0;
    border-top-right-radius: 0;
    border-bottom-left-radius: 0;
    &:not(:last-child) {
        border-bottom-right-radius: 0;
    }
}

.author-wrapper {
    flex: 1 1 auto;
}
</style>

<style lang="less">
@import '~mixins.less';

.submission-uploader {
    .deadline-information {
        flex: 1 1 auto;

        .input-group-text {
            width: 100%;
            background-color: transparent !important;

            @{dark-mode} {
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

    #git-instructions-modal .modal-dialog,
    #wrong-files-modal .modal-dialog {
        display: flex;
        flex-direction: column;
        height: auto;
        min-width: 75vw;
        margin: 12.5vh auto;
        max-width: 768px;

        @media @media-small {
            margin: 1rem auto;
        }

        .missing-required-files-content {
            min-height: 0;
            display: flex;
            flex-direction: column;
        }
    }

    #wrong-files-modal .modal-dialog {
        max-height: 75vh;

        @media @media-small {
            max-height: ~'calc(100vh - 2rem)';
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

    // See bug: https://github.com/vuejs/vue-loader/issues/1259
    .submission-limiting {
        .user {
            display: inline;
        }
    }
}

.hide-button {
    float: right;
    cursor: pointer;
    opacity: 0.75;
    margin: 0 0 0.25rem 0.5rem;

    &:hover {
        opacity: 1;
    }
}
</style>
