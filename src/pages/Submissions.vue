<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<loader center v-if="loading"/>
<div class="submission-list" v-else>
    <submission-list
        :assignment="assignment"
        :submissions="submissions"
        :canDownload="canDownload"
        :rubric="rubric"
        :graders="graders"
        :can-see-assignee="canSeeAssignee"
        :can-assign-grader="canAssignGrader"
        @assigneeUpdated="updateAssignee"/>

    <div v-if="canUpload">
        <b-popover target="submission-file-uploader-wrapper"
                   placement="top"
                   v-if="fileUploaderDisabled"
                   triggers="hover">
            <span>
                {{ fileUploaderDisabledMessage }}
            </span>
        </b-popover>
        <span id="submission-file-uploader-wrapper">
            <submission-uploader :assignment="assignment"
                                 :for-others="canUploadForOthers"
                                 :can-list-users="canListUsers"
                                 :disabled="fileUploaderDisabled"
                                 @created="goToSubmission"/>
        </span>
    </div>
</div>
</template>

<script>
import { SubmissionList, Loader, SubmitButton, SubmissionUploader } from '@/components';
import { mapGetters, mapActions } from 'vuex';

import * as assignmentState from '../store/assignment-states';

import { setPageTitle, pageTitleSep } from './title';

export default {
    name: 'submissions-page',

    data() {
        return {
            loading: true,
            canUpload: false,
            canUploadForOthers: false,
            canDownload: false,
            canListUsers: null,
            canSeeAssignee: false,
            canAssignGrader: false,
            wrongFiles: [],
        };
    },

    computed: {
        ...mapGetters('courses', ['assignments']),

        assignment() {
            return this.assignments[this.assignmentId];
        },

        submissions() {
            return (this.assignment && this.assignment.submissions) || [];
        },

        rubric() {
            return (this.assignment && this.assignment.rubric) || null;
        },

        graders() {
            return (this.assignment && this.assignment.graders) || null;
        },

        assignmentId() {
            return Number(this.$route.params.assignmentId);
        },

        courseId() {
            return this.$route.params.courseId;
        },

        fileUploaderDisabledMessage() {
            if (this.assignment.is_lti && !this.$inLTI) {
                return 'You can only submit this assignment from within your LMS';
            } else if (this.$inLTI && this.$LTIAssignmentId == null) {
                return "You didn't launch the assignment using LTI, please navigate to the 'Assignments' page and submit your work there.";
            } else if (this.$inLTI &&
                       this.assignmentId !== this.$LTIAssignmentId) {
                return 'You launched CodeGrade for a different assignment. Please retry opening the correct assignment.';
            } else {
                return undefined;
            }
        },

        fileUploaderDisabled() {
            if (this.assignment.is_lti && !this.$inLTI) {
                return true;
            } else if (this.$inLTI && this.$LTIAssignmentId == null) {
                return true;
            } else if (this.$inLTI &&
                       this.assignmentId !== this.$LTIAssignmentId) {
                return true;
            } else {
                return false;
            }
        },
    },

    watch: {
        submissions(newVal) {
            if (newVal.length === 0) {
                this.loadData();
            }
        },

        assignment(newVal, oldVal) {
            if (oldVal != null &&
                    newVal.id !== oldVal.id &&
                    !this.loading
            ) {
                this.loadData();
            }
        },
    },

    mounted() {
        this.loadData();
    },

    methods: {
        ...mapActions('courses', {
            loadCourses: 'loadCourses',
            loadSubmissions: 'loadSubmissions',
            updateSubmission: 'updateSubmission',
        }),

        loadData() {
            this.loading = true;
            Promise.all([
                this.loadSubmissions(this.assignmentId),
                this.$hasPermission(
                    [
                        'can_see_assignee',
                        'can_assign_graders',
                        'can_submit_own_work',
                        'can_submit_others_work',
                        'can_see_others_work',
                        'can_see_grade_before_open',
                        'can_upload_after_deadline',
                        'can_list_course_users',
                    ],
                    this.courseId,
                ),
            ]).then(([, [
                seeAssignee, assignGrader, submitOwn, submitOthers, others, before,
                afterDeadline, canList,
            ]]) => {
                setPageTitle(`${this.assignment.name} ${pageTitleSep} Submissions`);
                this.canSeeAssignee = seeAssignee;
                this.canAssignGrader = assignGrader;
                this.canUploadForOthers = submitOthers;
                this.canListUsers = canList;
                this.canUpload = (
                    (submitOwn || submitOthers) &&
                        (this.assignment.state === assignmentState.SUBMITTING ||
                            (afterDeadline && this.assignment.state !== assignmentState.HIDDEN))
                );

                if (others) {
                    if (this.assignment.state === assignmentState.DONE) {
                        this.canDownload = true;
                    } else {
                        this.canDownload = before;
                    }
                }

                this.loading = false;
            }, (err) => {
                // TODO: visual feedback
                // eslint-disable-next-line
                console.dir(err);
            });
        },

        goToSubmission(submission) {
            this.$router.push({
                name: 'submission',
                params: { submissionId: submission.id },
            });
        },

        updateAssignee(submission, assignee) {
            this.updateSubmission({
                assignmentId: this.assignmentId,
                submissionId: submission.id,
                submissionProps: { assignee },
            });
        },
    },

    components: {
        SubmissionUploader,
        SubmissionList,
        Loader,
        SubmitButton,
    },
};
</script>

<style lang="less" scoped>
.loader {
    padding-top: 3.5em;
}

#wrong-files-modal ul {
    max-height: 50vh;
    overflow-y: auto;

}
</style>
