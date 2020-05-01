<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div v-if="error != null" class="mt-3">
    <b-alert show variant="danger">
        {{ error }}
    </b-alert>
</div>
<loader center class="submission-page-loader" v-else-if="loadingPage"/>
<div class="page submission outer-container" id="submission-page" v-else>
    <local-header :back-route="submissionsRoute"
                  back-popover="Go back to submissions list"
                  always-show-extra-slot
                  :force-extra-drawer="!$root.$isLargeWindow">
        <submission-nav-bar
            :current-submission="submission"
            :latest-submissions="latestSubmissions"
            :not-latest="!currentSubmissionIsLatest"
            :group-of-user="groupOfCurrentUser"
            :show-user-buttons="canGrade"
            :assignment="assignment"/>

        <b-button-group class="submission-header-buttons">
            <preference-manager in-popover
                                container="#submission-page"
                                :file-id="prefFileId"
                                :show-context-amount="selectedCat === 'feedback-overview' || selectedCat === 'teacher-diff'"
                                :show-language="selectedCat === 'code'"
                                @whitespace="whitespaceChanged"
                                @language="languageChanged"
                                @inline-feedback="inlineFeedbackChanged" />

            <general-feedback-area v-if="editable"
                                   in-popover
                                   container="#submission-page"
                                   :assignment="assignment"
                                   :submission="submission"
                                   :editable="true" />

            <b-button v-if="canSeeGradeHistory"
                      id="codeviewer-grade-history"
                      v-b-popover.hover.top="'Show grade history'">
                <icon name="history"/>

                <b-popover target="codeviewer-grade-history"
                           title="Grade history"
                           triggers="click blur"
                           container="submission-page"
                           placement="bottom"
                           custom-class="p-0"
                           @show="$root.$emit('bv::hide::popover')">
                    <grade-history style="width: 30rem;"
                                   :submission-id="submission && submission.id"
                                   :isLTI="assignment && assignment.course.is_lti"/>
                </b-popover>
            </b-button>

            <b-button v-if="canEmailStudents"
                      id="codeviewer-email-student"
                      v-b-popover.top.hover="`Email the author${submission.user.isGroup ? 's' : ''} of this submission`"
                      v-b-modal.codeviewer-email-student-modal>
                <icon name="envelope"/>
            </b-button>

            <b-modal v-if="canEmailStudents"
                     id="codeviewer-email-student-modal"
                     ref="contactStudentModal"
                     size="xl"
                     hide-footer
                     no-close-on-backdrop
                     no-close-on-esc
                     hide-header-close
                     title="Email authors"
                     @show="() => $root.$emit('bv::hide::popover')"
                     body-class="p-0"
                     dialog-class="auto-test-result-modal">
                <cg-catch-error capture>
                    <template slot-scope="{ error }">
                        <b-alert v-if="error"
                                 show
                                 variant="danger">
                            {{ $utils.getErrorMessage(error) }}
                        </b-alert>

                        <student-contact
                            v-else
                            :initial-users="submission.user.getContainedUsers()"
                            :course="assignment.course"
                            :default-subject="defaultEmailSubject"
                            no-everybody-email-option
                            @hide="() => $refs.contactStudentModal.hide()"
                            @emailed="() => $refs.contactStudentModal.hide()"
                            :can-use-snippets="canUseSnippets"
                            class="p-3"/>
                    </template>
                </cg-catch-error>
            </b-modal>

            <b-button v-b-popover.hover.top="'Download assignment or feedback'"
                      id="codeviewer-download-toggle">
                <icon name="download"/>

                <b-popover target="codeviewer-download-toggle"
                           triggers="click blur"
                           placement="bottom"
                           container="submission-page"
                           custom-class="p-0"
                           @show="$root.$emit('bv::hide::popover')">
                    <table style="width: 10rem;"
                           class="table table-hover mb-0 text-left">
                        <tbody>
                            <tr @click="downloadType('zip')">
                                <td><b>Archive</b></td>
                            </tr>
                            <tr v-if="canSeeGrade || canSeeUserFeedback || canSeeLinterFeedback"
                                @click="downloadType('feedback')">
                                <td><b>Feedback</b></td>
                            </tr>
                        </tbody>
                    </table>
                </b-popover>
            </b-button>

            <submit-button v-if="canDeleteSubmission"
                           variant="danger"
                           confirm="By deleting all information about this submission, including files, will be lost forever! So are you really sure?"
                           confirm-in-modal
                           v-b-popover.hover.top="'Delete submission'"
                           :submit="deleteSubmission"
                           @after-success="afterDeleteSubmission">
                <icon name="times"/>
            </submit-button>
        </b-button-group>

        <template slot="extra" v-if="!loadingInner">
            <category-selector slot="extra"
                                :default="defaultCat"
                                v-model="selectedCat"
                                :categories="categories"/>
        </template>
    </local-header>

    <loader page-loader
            class="submission-page-inner-loader"
            v-if="loadingInner"/>
    <template v-else>
        <div class="cat-wrapper"
             :class="{ hidden: selectedCat !== 'code' }">
            <component v-if="!hiddenCats.has('code')"
                       :is="$root.$isLargeWindow ? 'rs-panes' : 'div'"
                       allow-resize
                       split-to="columns"
                       @update:size="splitRatio = $event"
                       :size="splitRatio"
                       :step="50"
                       units="percents"
                       class="code-wrapper"
                       id="submission-page-inner"
                       :min-size="30"
                       :max-size="85">
                <file-viewer slot="firstPane"
                             :assignment="assignment"
                             :submission="submission"
                             :file="currentFile"
                             :revision="revision"
                             :editable="canSeeUserFeedback && canGiveLineFeedback"
                             :can-use-snippets="canUseSnippets"
                             :show-whitespace="showWhitespace"
                             :show-inline-feedback="selectedCat === 'code' && showInlineFeedback && revision === 'student'"
                             :language="selectedLanguage"
                             @language="languageChanged" />

                <div class="submission-sidebar d-flex flex-column border rounded p-0 mt-3 mt-lg-0"
                     slot="secondPane">
                    <div v-if="sidebarTabs.length > 0"
                         class="flex-grow-0 d-flex flex-row border-bottom text-center cursor-pointer">
                        <a v-for="tab in sidebarTabs"
                           :key="tab.id"
                           class="submission-sidebar-tab p-1 border-right"
                           :class="{ active: currentSidebarTab === tab.id }"
                           v-b-popover.top.hover.window="tab.help"
                           @click.prevent="currentSidebarTab = tab.id">
                            <icon v-if="tab.icon"
                                  :name="tab.icon"
                                  class="mr-1"
                                  style="transform: translateY(-2px);"/>
                            {{ tab.name }}
                        </a>
                    </div>

                    <file-tree v-if="currentSidebarTab === 'files'"
                               class="flex-grow-1"
                               :assignment="assignment"
                               :submission="submission"
                               :revision="revision" />

                    <previous-feedback v-if="currentSidebarTab === 'feedback'"
                                       :submission="submission" />
                </div>
            </component>
        </div>

        <div class="cat-wrapper"
             :class="{ hidden: selectedCat !== 'feedback-overview' }">
            <feedback-overview v-if="!hiddenCats.has('feedback-overview')"
                               :assignment="assignment"
                               :submission="submission"
                               :show-whitespace="showWhitespace"
                               :show-inline-feedback="selectedCat === 'feedback-overview'" />
        </div>

        <div class="cat-wrapper"
             :class="{ hidden: selectedCat !== 'teacher-diff' }">
            <diff-overview v-if="!hiddenCats.has('teacher-diff')"
                           :assignment="assignment"
                           :submission="submission"
                           :show-whitespace="showWhitespace"/>
        </div>

        <div class="cat-wrapper"
             :class="{ hidden: selectedCat !== 'auto-test' }"
             v-if="autoTestId">
            <div class="cat-scroller border rounded">
                <auto-test :assignment="assignment"
                           :submission-id="submissionId" />
            </div>
        </div>
    </template>

    <grade-viewer :assignment="assignment"
                  :submission="submission"
                  :not-latest="!currentSubmissionIsLatest"
                  :group-of-user="groupOfCurrentUser"
                  :editable="canSeeGrade && editable"
                  :rubric-start-open="rubricStartOpen"
                  v-if="!loadingInner"
                  class="mb-3"/>
</div>
</template>

<script>
import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/download';
import 'vue-awesome/icons/edit';
import 'vue-awesome/icons/times';
import 'vue-awesome/icons/exclamation-triangle';
import 'vue-awesome/icons/history';
import 'vue-awesome/icons/archive';
import 'vue-awesome/icons/envelope';
import 'vue-awesome/icons/comment';
import 'vue-awesome/icons/folder';
import ResSplitPane from 'vue-resize-split-pane';

import { mapGetters, mapActions } from 'vuex';

import { nameOfUser } from '@/utils';

import * as assignmentState from '@/store/assignment-states';

import { setPageTitle } from '@/pages/title';

import {
    AutoTest,
    FeedbackOverview,
    DiffOverview,
    FileTree,
    CategorySelector,
    GradeViewer,
    GradeHistory,
    GeneralFeedbackArea,
    PreviousFeedback,
    Loader,
    LocalHeader,
    PreferenceManager,
    SubmissionNavBar,
    SubmitButton,
    Toggle,
    User,
} from '@/components';

import FileViewer from '@/components/FileViewer';
import StudentContact from '@/components/StudentContact';

export default {
    name: 'submission-page',

    data() {
        return {
            assignmentState,

            selectedCat: '',
            hiddenCats: new Set(),

            splitRatio: 75,
            currentSidebarTab: 'files',

            showWhitespace: true,
            selectedLanguage: 'Default',
            showInlineFeedback: true,
            currentFile: null,

            error: null,
        };
    },

    computed: {
        ...mapGetters('pref', ['contextAmount', 'fontSize']),
        ...mapGetters('user', {
            userId: 'id',
            userPerms: 'permissions',
        }),
        ...mapGetters('submissions', {
            storeGetLatestSubmissions: 'getLatestSubmissions',
            storeGetSingleSubmission: 'getSingleSubmission',
            storeGetGroupSubmissionOfUser: 'getGroupSubmissionOfUser',
        }),
        ...mapGetters('courses', ['courses', 'assignments']),
        ...mapGetters('autotest', {
            allAutoTests: 'tests',
        }),
        ...mapGetters('fileTrees', ['getFileTree']),
        ...mapGetters('feedback', ['getFeedback']),

        course() {
            const id = Number(this.$route.params.courseId);
            return this.courses[id];
        },

        courseId() {
            return this.$utils.getProps(this.course, null, 'id');
        },

        assignment() {
            const id = Number(this.$route.params.assignmentId);
            return this.assignments[id];
        },

        assignmentId() {
            return this.$utils.getProps(this.assignment, null, 'id');
        },

        submission() {
            const id = Number(this.$route.params.submissionId);
            return this.storeGetSingleSubmission(this.assignmentId, id);
        },

        submissionId() {
            return this.$utils.getProps(this.submission, null, 'id');
        },

        fileId() {
            return this.$route.params.fileId;
        },

        editable() {
            return !!(
                this.canGrade &&
                this.currentSubmissionIsLatest &&
                this.groupOfCurrentUser == null
            );
        },

        coursePerms() {
            return this.$utils.getProps(this.assignment, {}, 'course', 'permissions');
        },

        canGrade() {
            return this.coursePerms.can_grade_work;
        },

        canSeeGrade() {
            return this.assignment && this.assignment.canSeeGrade();
        },

        canSeeUserFeedback() {
            return this.assignment && this.assignment.canSeeUserFeedback();
        },

        canSeeLinterFeedback() {
            return this.assignment && this.assignment.canSeeLinterFeedback();
        },

        canDeleteSubmission() {
            return this.coursePerms.can_delete_submission;
        },

        canSeeGradeHistory() {
            return this.coursePerms.can_see_grade_history;
        },

        canEmailStudents() {
            return (UserConfig.features.email_students &&
                    this.$utils.getProps(this.coursePerms, false, 'can_email_students'));
        },

        canViewAutoTestBeforeDone() {
            return this.coursePerms.can_view_autotest_before_done;
        },

        canGiveLineFeedback() {
            return this.editable && this.revision === 'student';
        },

        canUseSnippets() {
            return !!this.userPerms.can_use_snippets;
        },

        prefFileId() {
            switch (this.selectedCat) {
                case 'code':
                    return this.fileId;
                case 'feedback-overview':
                    return `${this.submissionId}-feedback-overview`;
                case 'auto-test':
                    return `${this.submissionId}-auto-test`;
                case 'teacher-diff':
                    return `${this.submissionId}-teacher-diff`;
                default:
                    return '';
            }
        },

        revision() {
            return this.$route.query.revision || 'student';
        },

        latestSubmissions() {
            return this.storeGetLatestSubmissions(this.assignmentId);
        },

        currentSubmissionIsLatest() {
            return !!this.latestSubmissions.find(sub => sub.id === this.submissionId);
        },

        groupOfCurrentUser() {
            const curSub = this.submission;
            if (curSub == null) {
                return null;
            }
            const groupSub = this.storeGetGroupSubmissionOfUser(this.assignmentId, curSub.userId);
            return this.$utils.getProps(groupSub, null, 'user');
        },

        fileTree() {
            return this.getFileTree(this.assignmentId, this.submissionId);
        },

        feedback() {
            return this.getFeedback(this.assignmentId, this.submissionId);
        },

        autoTestId() {
            return this.assignment && this.assignment.auto_test_id;
        },

        autoTest() {
            return this.allAutoTests[this.autoTestId];
        },

        autoTestRun() {
            return this.$utils.getProps(this.autoTest, null, 'runs', 0);
        },

        autoTestResult() {
            return this.autoTestRun && this.autoTestRun.findResultBySubId(this.submissionId);
        },

        loadingPage() {
            return !this.assignment || this.submission == null;
        },

        loadingInner() {
            const {
                canSeeUserFeedback,
                canSeeLinterFeedback,
                feedback,
                fileTree,
                currentFile,
                canViewAutoTest,
                autoTest,
            } = this;

            return (
                ((canSeeUserFeedback || canSeeLinterFeedback) && !feedback) ||
                !fileTree ||
                !currentFile ||
                (canViewAutoTest && !autoTest)
            );
        },

        canViewAutoTest() {
            const { autoTestId, assignmentDone, canViewAutoTestBeforeDone } = this;

            return autoTestId && (assignmentDone || canViewAutoTestBeforeDone);
        },

        showTeacherDiff() {
            return this.fileTree && this.fileTree.hasRevision(this.fileTree.student);
        },

        categories() {
            return [
                {
                    id: 'code',
                    name: 'Code',
                    enabled: true,
                },
                {
                    id: 'feedback-overview',
                    name: 'Feedback overview',
                    badge: this.numFeedbackItems === 0 ? null : {
                        label: this.numFeedbackItems,
                        variant: 'primary',
                    },
                    enabled: true,
                },
                {
                    id: 'auto-test',
                    name: 'AutoTest',
                    badge: !this.showContinuousBadge ? null : {
                        label: 'CF',
                        variant: 'warning',
                    },
                    enabled: this.autoTestId != null,
                },
                {
                    id: 'teacher-diff',
                    name: 'Teacher diff',
                    enabled: this.showTeacherDiff,
                },
            ];
        },

        sidebarTabs() {
            const tabs = [
                {
                    id: 'files',
                    name: 'Files',
                    help: 'Show the files of this submission.',
                    icon: 'folder',
                },
            ];

            if (this.canSeeUserFeedback) {
                tabs.push({
                    id: 'feedback',
                    name: 'Feedback',
                    help: 'Show feedback given on previous assignments in this course.',
                    icon: 'comment',
                });
            }

            return tabs;
        },

        hasFeedback() {
            const fb = this.feedback;

            return !!(fb && (fb.general || Object.keys(fb.user).length));
        },

        numFeedbackItems() {
            if (!this.feedback || !this.submission) {
                return 0;
            }
            return this.feedback.countEntries();
        },

        showContinuousBadge() {
            const test = this.autoTest;
            const result = this.autoTestResult;

            // Check that result.isFinal is exactly false, because it may be
            // `undefined` when we haven't received the extended result yet,
            // which would cause the CF badge to flicker on page load.
            return (
                test &&
                test.results_always_visible &&
                ((result && result.isFinal === false) || !this.canSeeGrade)
            );
        },

        assignmentDone() {
            if (this.assignment == null) {
                return false;
            } else {
                return this.assignment.state === assignmentState.DONE;
            }
        },

        defaultCat() {
            const editable = this.editable;
            const done = this.assignmentDone;
            const hasFb = this.hasFeedback;
            const testRun = this.autoTestRun;

            if (done) {
                if (hasFb) {
                    return 'feedback-overview';
                } else if (testRun) {
                    return 'auto-test';
                } else {
                    return 'feedback-overview';
                }
            } else if (!editable && testRun) {
                return 'auto-test';
            } else {
                return 'code';
            }
        },

        rubricStartOpen() {
            const done = this.assignmentDone;
            const editable = this.editable;
            const canSeeGrade = this.canSeeGrade;

            return (editable || done) && canSeeGrade;
        },

        submissionsRoute() {
            return {
                name: 'assignment_submissions',
                params: {
                    courseId: this.courseId,
                    assignmentId: this.assignmentId,
                },
                query: {
                    q: this.$route.query.search || undefined,
                    mine: this.$route.query.mine || false,
                    latest: this.$route.query.latest || false,
                    sortBy: this.$route.query.sortBy,
                    sortAsc: this.$route.query.sortAsc,
                    page: this.$route.query.page || undefined,
                },
            };
        },

        pageTitle() {
            const assig = this.assignment;
            const sub = this.submission;
            const grade = sub && sub.grade;

            if (!assig) {
                return '';
            }

            let title = this.assignment.name;
            if (sub) {
                title += ` by ${nameOfUser(sub.user)}`;

                if (grade != null) {
                    title += ` (${grade})`;
                }
            }

            return title;
        },

        defaultEmailSubject() {
            return `[CodeGrade - ${this.assignment.course.name}/${this.assignment.name}] …`;
        },
    },

    watch: {
        assignmentId: {
            immediate: true,
            handler() {
                if (this.assignmentId != null) {
                    this.storeLoadSubmissions(this.assignmentId);
                }
            },
        },

        autoTestId: {
            immediate: true,
            handler() {
                this.loadAutoTest();
            },
        },

        submissionId: {
            immediate: true,
            handler() {
                this.loadData();
            },
        },

        // We need these watchers (feedback and filetree) as these properties
        // become `null`/`undefined` when the submissions are reloaded (this can
        // be done using the sidebar). So in that case we need to load the data
        // again.
        feedback() {
            if (!this.feedback) {
                this.loadData();
            }
        },

        fileTree() {
            if (!this.fileTree) {
                this.loadData();
            }
        },

        fileId: {
            immediate: true,
            handler() {
                this.openFile();
            },
        },

        revision: {
            immediate: true,
            handler() {
                this.openFile();
            },
        },

        pageTitle: {
            immediate: true,
            handler() {
                setPageTitle(this.pageTitle);
            },
        },

        selectedCat: {
            immediate: true,
            handler() {
                this.hiddenCats.delete(this.selectedCat);
            },
        },

        currentSidebarTab: {
            immediate: true,
            handler(newVal) {
                if (newVal === 'feedback') {
                    this.splitRatio = Math.min(50, this.splitRatio);
                }
            },
        },
    },

    methods: {
        ...mapActions('submissions', {
            storeLoadSubmissions: 'loadSubmissions',
            storeLoadSingleSubmission: 'loadSingleSubmission',
            storeDeleteSubmission: 'deleteSubmission',
        }),
        ...mapActions('feedback', {
            storeLoadFeedback: 'loadFeedback',
        }),
        ...mapActions('fileTrees', {
            storeLoadFileTree: 'loadFileTree',
        }),

        ...mapActions('autotest', {
            storeLoadAutoTest: 'loadAutoTest',
            storeLoadAutoTestResult: 'loadAutoTestResult',
        }),

        loadCurrentSubmission() {
            // We need to reset the current file to `null` as changing the
            // current submission reloads the current file, which means we
            // download it again while it is not needed.
            this.currentFile = null;

            // Reset the error so we show a loader and not the old error.
            this.error = null;

            return this.storeLoadSingleSubmission({
                assignmentId: this.assignmentId,
                submissionId: this.submissionId,
            }).catch(err => {
                this.error = this.$utils.getErrorMessage(err);
            });
        },

        async loadData() {
            if (this.submissionId == null) {
                return;
            }

            if (!this.$route.query.revision) {
                this.$router.replace(
                    this.$utils.deepExtend({}, this.$route, {
                        query: { revision: 'student' },
                    }),
                );
            }

            this.currentFile = null;
            this.showWhitespace = true;

            this.hiddenCats = new Set(
                this.categories.filter(c => c.id !== this.selectedCat).map(c => c.id),
            );

            const promises = [
                this.storeLoadFileTree({
                    assignmentId: this.assignmentId,
                    submissionId: this.submissionId,
                }),
                this.storeLoadFeedback({
                    assignmentId: this.assignmentId,
                    submissionId: this.submissionId,
                }),
            ];

            // Load the AutoTest result of this submission. This must happen here because the
            // AutoTest file tree must be loaded for `loadingInner` to become `false` if the
            // file id in the URL refers to a file in the AutoTest file tree, because
            // `loadingInner` waits until `currentFile` is set.
            if (this.autoTestId != null && this.autoTestResult == null) {
                promises.push(
                    this.storeLoadAutoTestResult({
                        autoTestId: this.autoTestId,
                        submissionId: this.submissionId,
                    }).catch(() => {}),
                );
            }

            await Promise.all(promises).then(this.openFirstFile);
        },

        loadAutoTest() {
            if (this.autoTestId != null) {
                return this.storeLoadAutoTest({
                    autoTestId: this.autoTestId,
                });
            } else {
                return Promise.resolve();
            }
        },

        openFirstFile() {
            if (!this.fileTree) {
                return;
            }

            let file;
            if (this.fileId) {
                file = this.fileTree.search(this.revision, this.fileId);

                if (!file && this.currentFile && this.currentFile.revision) {
                    file = this.fileTree.search(this.revision, this.currentFile.revision.id);
                }
            }

            if (!file) {
                file = this.fileTree.getFirstFile(this.revision);
            }

            if (file) {
                const fileId = file.id || file.ids[0] || file.ids[1];
                if (fileId !== this.fileId) {
                    this.$router.replace(
                        this.$utils.deepExtend({}, this.$route, {
                            name: 'submission_file',
                            params: { fileId },
                        }),
                    );
                }
            }

            this.currentFile = file;
        },

        openFile() {
            this.currentFile = this.fileTree && this.fileTree.search(this.revision, this.fileId);
        },

        deleteSubmission() {
            const sub = this.submission;
            return this.$http.delete(`/api/v1/submissions/${this.submissionId}`).then(() => sub);
        },

        afterDeleteSubmission(sub) {
            this.storeDeleteSubmission({
                assignmentId: this.assignmentId,
                submission: sub,
            });
            this.$router.replace({
                name: 'assignment_submissions',
                params: {
                    courseId: this.courseId,
                    assignmentId: this.assignmentId,
                },
            });
        },

        downloadType(type) {
            this.$http
                .get(this.$utils.buildUrl(
                    ['api', 'v1', 'submissions', this.submissionId],
                    { query: { type } },
                ))
                .then(({ data }) => {
                    const url = this.$utils.buildUrl(
                        ['api', 'v1', 'files', data.name, data.output_name],
                        { query: { not_as_attachment: '' } },
                    );
                    window.open(url);
                });
        },

        languageChanged(val) {
            this.selectedLanguage = val;
        },

        whitespaceChanged(val) {
            this.showWhitespace = val;
        },

        inlineFeedbackChanged(val) {
            this.showInlineFeedback = val;
        },
    },

    components: {
        AutoTest,
        CategorySelector,
        DiffOverview,
        FeedbackOverview,
        FileTree,
        FileViewer,
        GradeViewer,
        GradeHistory,
        GeneralFeedbackArea,
        PreviousFeedback,
        Loader,
        LocalHeader,
        PreferenceManager,
        SubmissionNavBar,
        SubmitButton,
        Toggle,
        Icon,
        User,
        StudentContact,
        'rs-panes': ResSplitPane,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.outer-container {
    display: flex;
    flex-direction: column;
    flex: 1 1 auto;
    height: 100vh;
    max-height: 100%;
    margin-bottom: 0 !important;
    overflow: hidden;
}

.submission-nav-bar {
    flex: 1 1 auto;
}

.cat-wrapper {
    position: relative;
    flex: 1 1 100%;
    min-height: 0;
    margin: 0 -15px 1rem;
    padding: 0 1rem;
    transition: opacity .25s ease-out, visibility .25s ease-out;
    overflow: hidden;
    visibility: visible;

    &.hidden {
        visibility: hidden;
        padding: 0;
        margin: 0;
        opacity: 0;
        max-height: 0;
        overflow-y: hidden;
    }
}

.cat-scroller {
    max-height: 100%;
    overflow: auto;
}

.code-wrapper {
    display: flex;
    flex-wrap: nowrap;
    min-height: 0;
    height: 100%;

    @media @media-no-large {
        flex-direction: column;
    }
}

.file-viewer {
    position: relative;
    min-height: 0;
    max-height: 100%;

    @media @media-no-large {
        height: 100%;
    }
}

.submission-sidebar {
    max-height: 100%;

    @media @media-no-large {
        flex: 0 0 auto;
    }

    & .submission-sidebar-tab {
        flex: 0 0 50%;
        color: @color-secondary;

        &.active {
            background-color: rgba(0, 0, 0, 0.025);
        }

        &:hover {
            background-color: rgba(0, 0, 0, 0.05);
        }

        &:last-child {
            border-right: 0 !important;
        }
    }
}

.file-tree,
.previous-feedback {
    min-height: 0;
    max-height: 100%;

    @media @media-no-large {
        max-height: 15vh;
    }
}

.file-tree {
    overflow: auto;
}

.previous-feedback {
    overflow: hidden;
}

.grade-viewer {
    flex: 0 0 auto;
}
</style>

<style lang="less">
@import '~mixins.less';

#submission-page {
    .popover {
        max-width: 45em;
    }

    .code-wrapper.pane-rs {
        position: relative;
    }

    .code-wrapper .Resizer {
        z-index: 0;
    }

    .code-wrapper > .Resizer.columnsres {
        background-color: transparent !important;
        border: none !important;
        width: 1rem !important;
        margin: 0 !important;
        position: relative;

        &:before,
        &:after {
            content: '';
            display: block;
            width: 3px;
            height: 3px;
            border-radius: 50%;
            background-color: gray;
            position: absolute;
            top: 50%;
            left: 50%;
            z-index: 10;
        }

        &:before {
            transform: translate(-2px, -4px);
        }

        &:after {
            transform: translate(-2px, +1px);
        }
    }

    .category-selector .badge {
        font-size: 1em !important;
    }
}
</style>
