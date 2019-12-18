<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="manage-assignment loading" v-if="loading">
    <local-header>
        <template slot="title" v-if="assignment && Object.keys(assignment).length">
            <span>{{ assignment.name }}</span>
            <small v-if="formattedDeadline">- {{ formattedDeadline }}</small>
            <small v-else class="text-muted"><i>- No deadline</i></small>
        </template>
        <loader :scale="1"/>
    </local-header>
    <loader page-loader/>
</div>
<div class="manage-assignment" v-else>
    <local-header always-show-extra-slot
                  class="header">
        <template slot="title">
            <span>{{ assignment.name }}</span>
            <small v-if="formattedDeadline">- {{ formattedDeadline  }}</small>
            <small v-else class="text-muted"><i>- No deadline</i></small>
        </template>
        <assignment-state :assignment="assignment"
                          :key="assignmentId"
                          class="assignment-state"
                          :editable="canEditState"
                          size="sm"/>
        <template slot="extra">
            <hr class="mt-2 mb-1" />

            <category-selector default="general"
                               v-model="selectedCat"
                               :categories="categories"/>
        </template>
    </local-header>

    <div class="page-content" v-if="loadingInner">
        <loader page-loader />
    </div>
    <div class="page-content" v-show="!loadingInner"
         :key="assignmentId">
        <div :class="{hidden: selectedCat !== 'general'}"
             class="row cat-wrapper">
            <div v-if="canEditInfo"
                 class="col-lg-12">
                <b-form-fieldset v-if="canEditName">
                    <b-input-group prepend="Name">
                        <input type="text"
                               class="form-control"
                               v-model="assignmentTempName"
                               @keyup.ctrl.enter="$refs.updateName.onClick"/>
                        <b-input-group-append>
                            <submit-button :submit="submitName"
                                           @success="updateName"
                                           ref="updateName"/>
                        </b-input-group-append>
                    </b-input-group>
                </b-form-fieldset>

                <b-form-fieldset v-if="canEditDeadline">
                    <b-input-group>
                        <b-input-group-prepend is-text slot="prepend"
                                               :class="{ 'warning': assignment.deadline === null }">
                            Deadline

                            <description-popover placement="top">
                                <template v-if="ltiProvider && !ltiProvider.supportsDeadline"
                                          slot="description">
                                    {{ lmsName }} did not pass this assignment's deadline on to
                                    CodeGrade.  Students will not be able to submit their work
                                    until the deadline is set here.
                                </template>
                                <template v-else
                                          slot="description">
                                    Students will not be able to submit work unless a deadline has
                                    been set.
                                </template>
                            </description-popover>
                        </b-input-group-prepend>
                        <datetime-picker v-model="assignmentTempDeadline"
                                         placeholder="None set"/>
                        <b-input-group-append>
                            <submit-button :submit="submitDeadline"
                                           @success="updateDeadline"
                                           ref="updateDeadline"/>
                        </b-input-group-append>
                    </b-input-group>
                </b-form-fieldset>

                <b-form-fieldset v-if="canEditMaxGrade" class="flex-grow-1">
                    <maximum-grade :assignment-id="assignmentId"/>
                </b-form-fieldset>

                <b-form-fieldset v-if="canEditInfo">
                    <assignment-submit-types :assignment-id="assignmentId"/>
                </b-form-fieldset>
            </div>

            <div class="col-lg-12">
                <b-card v-if="canEditIgnoreFile"
                        class="ignore-card">
                    <span slot="header">
                        Hand-in requirements
                        <description-popover
                            description="This allows you to set hand-in
                                         requirement for students, making sure
                                         their submission follows a certain file
                                         and directory structure. Students will
                                         be able to see these requirements
                                         before submitting and will get a
                                         warning if their submission does not
                                         follow the hand-in requirements."/>
                    </span>
                    <c-g-ignore-file :assignment-id="assignmentId"/>
                </b-card>

                <b-card v-if="canEditGroups" no-body>
                    <span slot="header">
                        Group assignment
                        <description-popover>
                            <span slot="description">
                                Determine if this assignment should be a group
                                assignment. Select a group set for this
                                assignment to make it a group assignment. To
                                learn more about how groups work on CodeGrade, you can read
                                more <a class="inline-link"
                                        href="https://docs.codegra.de/"
                                        target="_blank">here</a>.
                            </span>
                        </description-popover>
                    </span>
                    <assignment-group :assignment="assignment"/>
                </b-card>
            </div>

            <div :class="canSubmitBbZip ? 'col-xl-6' : 'col-xl-12'">
                <b-card v-if="canSubmitWork" no-body>
                    <span slot="header">
                        Upload submission
                        <description-popover
                            description="Upload work for this assignment. With the
                                         author field you can select who should be the author. This
                                         function can be used to submit work for a student."/>
                    </span>
                    <submission-uploader :assignment="assignment"
                                         for-others
                                         no-border
                                         :can-list-users="permissions.can_list_course_users"/>
                </b-card>

                <b-card header="Danger zone"
                        class="danger-zone-wrapper"
                        border-variant="danger"
                        header-text-variant="danger"
                        header-border-variant="danger"
                        v-if="assignment.course.permissions.can_delete_assignments">
                    <div class="d-flex justify-content-between">
                        <div>
                            <strong class="d-block">Delete assignment</strong>

                            <small>
                                Delete this assignment, including all its
                                submissions.
                            </small>
                        </div>
                        <div>
                            <submit-button :submit="deleteAssignment"
                                           @after-success="afterDeleteAssignment"
                                           confirm="Deleting this assignment cannot be reversed, and all submissions will be lost."
                                           confirm-in-modal
                                           variant="danger">
                                Delete assignment
                            </submit-button>
                        </div>
                    </div>
                </b-card>
            </div>

            <div :class="canSubmitWork ? 'col-xl-6' : 'col-xl-12'">
                <b-card header="Blackboard zip"
                        v-if="canSubmitBbZip">
                    <b-popover placement="top"
                               v-if="assignment.is_lti"
                               :target="`file-uploader-assignment-${assignment.id}`"
                               triggers="hover">
                        Not available for LTI assignments
                    </b-popover>
                    <file-uploader class="blackboard-zip-uploader"
                                   :url="`/api/v1/assignments/${assignment.id}/submissions/`"
                                   :disabled="assignment.is_lti"
                                   @response="forceLoadSubmissions(assignment.id)"
                                   :id="`file-uploader-assignment-${assignment.id}`"/>
                </b-card>
            </div>
        </div>

        <div class="row cat-wrapper"
             :class="{hidden: selectedCat !== 'graders'}">
            <div class="col-xl-6">
                <b-card v-if="canAssignGraders" no-body>
                    <span slot="header">
                        Divide submissions
                        <description-popover>
                            <span slot="description">
                                Divide this assignment. When dividing users are
                                assigned to submissions based on weights.  When
                                new submissions are uploaded graders are also
                                automatically assigned. When graders assign
                                themselves the weights are not updated to
                                reflect this. To read more about dividing
                                graders please read our
                                documentation <a href="https://docs.codegra.de/user/management.html#dividing-submissions"
                                                 target="_blank"
                                                 class="inline-link"
                                                 >here</a>.
                            </span>
                        </description-popover>
                    </span>
                    <loader class="text-center" v-if="gradersLoading && !gradersLoadedOnce"/>
                    <divide-submissions :assignment="assignment"
                                        @divided="loadGraders"
                                        :graders="graders"
                                        v-else/>
                </b-card>
            </div>

            <div class="col-xl-6">
                <b-card v-if="canUpdateGradersStatus"
                        no-body
                        class="finished-grading-card">
                    <span slot="header">
                        Finished grading
                        <description-popover
                            description="Indicate that a grader is done with
                                         grading. All graders that have indicated that they
                                         are done will not receive notification e-mails."/>
                    </span>
                    <loader class="text-center" v-if="gradersLoading"/>
                    <finished-grader-toggles :assignment="assignment"
                                             :graders="graders"
                                             :others="permissions.can_update_grader_status || false"
                                             v-else/>
                </b-card>

                <b-card v-if="canUpdateNotifications">
                    <span slot="header">
                        Notifications
                        <description-popover
                            description="Send a reminder e-mail to the selected
                                         graders on the selected time if they have not yet
                                         finished grading."/>
                    </span>
                    <notifications :assignment="assignment"
                                   class="reminders"/>
                </b-card>
            </div>
        </div>

        <div class="cat-wrapper" :class="{hidden: selectedCat !== 'linters'}">
            <b-card v-if="canUseLinters"
                    header="Linters"
                    :course-id="assignment.course.id">
                <linters :assignment="assignment"/>
            </b-card>

        </div>

        <div class="cat-wrapper" :class="{hidden: selectedCat !== 'plagiarism'}">
            <b-card v-if="canUsePlagiarism" no-body>
                <span slot="header">
                    Plagiarism checking
                    <description-popover
                        description="Run a plagiarism checker or view
                                     the results."/>
                </span>
                <plagiarism-runner :assignment="assignment"
                                   :hidden="selectedCat !== 'plagiarism'"
                                   :can-manage="permissions.can_manage_plagiarism"
                                   :can-view="permissions.can_view_plagiarism"/>
            </b-card>
        </div>

        <div class="cat-wrapper" :class="{hidden: selectedCat !== 'rubric'}">
            <b-card header="Rubric" v-if="canUseRubrics">
                <!-- TODO: Properfix instead of :key hack -->
                <rubric-editor :key="assignment.id"
                               :assignment="assignment"
                               :hidden="selectedCat !== 'rubric'"
                               ref="rubricEditor"
                               editable/>
            </b-card>
        </div>

        <div class="cat-wrapper" :class="{hidden: selectedCat !== 'auto-test'}">
            <!-- TODO: Properfix instead of :key hack -->
            <auto-test :key="assignment.id"
                       :assignment="assignment"
                       :hidden="selectedCat !== 'auto-test'"
                       editable />
        </div>
    </div>
</div>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';

import { convertToUTC, readableFormatDate } from '@/utils';
import ltiProviders from '@/lti_providers';

import {
    AssignmentState,
    DivideSubmissions,
    FileUploader,
    Linters,
    Loader,
    SubmitButton,
    RubricEditor,
    CGIgnoreFile,
    Notifications,
    DescriptionPopover,
    FinishedGraderToggles,
    LocalHeader,
    SubmissionUploader,
    MaximumGrade,
    PlagiarismRunner,
    AssignmentGroup,
    CategorySelector,
    DatetimePicker,
    AutoTest,
    AssignmentSubmitTypes,
} from '@/components';

export default {
    name: 'manage-assignment',

    data() {
        return {
            UserConfig,
            graders: [],
            gradersLoading: true,
            gradersLoadedOnce: false,
            assignmentTempName: '',
            assignmentTempDeadline: '',
            permissions: null,
            loading: true,
            loadingInner: true,
            selectedCat: '',
        };
    },

    computed: {
        ...mapGetters('courses', ['assignments']),

        formattedDeadline() {
            return (this.assignment && this.assignment.formatted_deadline) || '';
        },

        assignmentId() {
            return Number(this.$route.params.assignmentId);
        },

        assignment() {
            return (this.assignments || {})[this.assignmentId] || {};
        },

        assignmentUrl() {
            return `/api/v1/assignments/${this.assignment.id}`;
        },

        lmsName() {
            return this.assignment.lms_name;
        },

        ltiProvider() {
            const lms = this.lmsName;
            return lms ? ltiProviders[lms] : null;
        },

        canEditState() {
            return this.permissions.can_edit_assignment_info;
        },

        canEditInfo() {
            return this.canEditName || this.canEditDeadline || this.canEditMaxGrade;
        },

        canEditName() {
            return !this.assignment.is_lti && this.permissions.can_edit_assignment_info;
        },

        canEditDeadline() {
            return (
                (!this.ltiProvider || !this.ltiProvider.supportsDeadline) &&
                this.permissions.can_edit_assignment_info
            );
        },

        canEditMaxGrade() {
            return (
                (!this.ltiProvider || this.ltiProvider.supportsBonusPoints) &&
                this.permissions.can_edit_maximum_grade
            );
        },

        canEditIgnoreFile() {
            return this.permissions.can_edit_cgignore;
        },

        canEditGroups() {
            return UserConfig.features.groups && this.permissions.can_edit_group_assignment;
        },

        canSubmitWork() {
            return this.permissions.can_submit_others_work;
        },

        canSubmitBbZip() {
            return this.permissions.can_upload_bb_zip && UserConfig.features.blackboard_zip_upload;
        },

        canAssignGraders() {
            return this.permissions.can_assign_graders;
        },

        canUpdateGradersStatus() {
            return this.permissions.can_update_grader_status || this.permissions.can_grade_work;
        },

        canUpdateNotifications() {
            return this.permissions.can_update_course_notifications;
        },

        canUseLinters() {
            return this.permissions.can_use_linter && UserConfig.features.linters;
        },

        canUsePlagiarism() {
            return this.permissions.can_manage_plagiarism || this.permissions.can_view_plagiarism;
        },

        canUseRubrics() {
            return this.permissions.manage_rubrics && UserConfig.features.rubrics;
        },

        canUseAutoTest() {
            return (
                (this.permissions.can_run_autotest ||
                    this.permissions.can_edit_autotest ||
                    this.permissions.can_delete_autotest_run) &&
                UserConfig.features.auto_test
            );
        },

        categories() {
            return [
                {
                    id: 'general',
                    name: 'General',
                    enabled:
                        this.canEditInfo ||
                        this.canEditIgnoreFile ||
                        this.canEditGroups ||
                        this.canSubmitWork ||
                        this.canSubmitBbZip,
                },
                {
                    id: 'graders',
                    name: 'Graders',
                    enabled:
                        this.canAssignGraders ||
                        this.canUpdateGradersStatus ||
                        this.canUpdateNotifications,
                },
                {
                    id: 'linters',
                    name: 'Linters',
                    enabled: this.canUseLinters,
                },
                {
                    id: 'plagiarism',
                    name: 'Plagiarism',
                    enabled: this.canUsePlagiarism,
                },
                {
                    id: 'rubric',
                    name: 'Rubric',
                    enabled: this.canUseRubrics,
                },
                {
                    id: 'auto-test',
                    name: 'AutoTest',
                    enabled: this.canUseAutoTest,
                },
            ];
        },

        manageGroupLink() {
            return {
                name: 'manage_course',
                params: {
                    course_id: this.assignment.course.id,
                },
                hash: '#groups',
            };
        },
    },

    watch: {
        assignmentId(newVal, oldVal) {
            if (oldVal && newVal !== oldVal) {
                this.loadData();
            }
        },
    },

    mounted() {
        this.loadData();
    },

    methods: {
        ...mapActions('courses', ['updateAssignment', 'loadCourses', 'reloadCourses']),
        ...mapActions('submissions', ['forceLoadSubmissions']),

        async loadData() {
            const setAssigData = () => {
                if (this.loading) {
                    this.permissions = this.assignment.course.permissions;
                    this.assignmentTempName = this.assignment.name;
                    this.assignmentTempDeadline = this.assignment.deadline;
                    this.loading = false;
                }
            };

            this.loading = true;
            this.loadingInner = true;

            if (this.assignment.id === this.assignmentId) {
                setAssigData();
            }

            await this.$afterRerender();

            this.loadGraders();

            return this.loadCourses().then(() => {
                setAssigData();
                this.loadingInner = false;
            });
        },

        async loadGraders() {
            if (!this.gradersLoading) {
                this.gradersLoading = true;
            }

            const { data } = await this.$http.get(
                `/api/v1/assignments/${this.assignmentId}/graders/`,
            );
            this.graders = data;
            this.gradersLoading = false;
            this.gradersLoadedOnce = true;
        },

        submitName() {
            return this.$http.patch(this.assignmentUrl, {
                name: this.assignmentTempName,
            });
        },

        updateName() {
            this.updateAssignment({
                courseId: this.assignment.course.id,
                assignmentId: this.assignment.id,
                assignmentProps: {
                    name: this.assignmentTempName,
                },
            });
        },

        submitDeadline() {
            return this.$http.patch(this.assignmentUrl, {
                deadline: convertToUTC(this.assignmentTempDeadline),
            });
        },

        updateDeadline() {
            this.updateAssignment({
                assignmentId: this.assignment.id,
                assignmentProps: {
                    deadline: this.assignmentTempDeadline,
                    formatted_deadline: readableFormatDate(this.assignmentTempDeadline),
                },
            });
        },

        deleteAssignment() {
            return this.$http.delete(`/api/v1/assignments/${this.assignment.id}`);
        },

        afterDeleteAssignment() {
            this.reloadCourses();
            this.$router.push({ name: 'home' });
        },
    },

    components: {
        AssignmentState,
        DivideSubmissions,
        FileUploader,
        Linters,
        Loader,
        SubmitButton,
        RubricEditor,
        CGIgnoreFile,
        Notifications,
        DescriptionPopover,
        FinishedGraderToggles,
        LocalHeader,
        SubmissionUploader,
        MaximumGrade,
        PlagiarismRunner,
        AssignmentGroup,
        CategorySelector,
        DatetimePicker,
        AutoTest,
        AssignmentSubmitTypes,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.assignment-title {
    margin-bottom: 0;
}

.manage-assignment.loading {
    display: flex;
    flex-direction: column;
}

.card {
    margin-bottom: 1em;
}

.card-header {
    font-size: 1.25rem;
    font-family: inherit;
    font-weight: 500;
    line-height: 1.2;
    color: inherit;
}

.plagiarism-runner {
    margin-bottom: 1rem;
}

.categories {
    display: flex;
    flex-direction: row;
}

.category {
    display: flex;
    flex-direction: column;

    margin-bottom: -1rem;
    line-height: 1rem;
    padding: 0 1rem;
    cursor: pointer;

    span {
        padding-bottom: 0.25rem;
        font-size: 0.75rem;
    }

    .icon {
        padding-bottom: 0rem;
        margin: 0 auto;
    }
}

.cat-wrapper {
    transition: opacity 0.25s ease-out;
    padding-top: 5px;

    &.hidden {
        padding: 0;
        transition: none;
        opacity: 0;
        max-height: 0;
        overflow-y: hidden;
    }
}

.manage-assignment .header {
    z-index: 9;
}

.finished-grading-card .loader {
    padding: 1rem;
}

.ignore-card .card-body {
    padding-top: 0.75rem;
}
</style>
