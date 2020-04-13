<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div v-if="error != null" class="mt-3">
    <b-alert show variant="danger">
        {{ error }}
    </b-alert>
</div>
<loader center v-else-if="loadingPage"/>
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
                     body-class="p-0"
                     dialog-class="auto-test-result-modal">
                <student-contact :initial-users="submission.user.getContainedUsers()"
                                 :course="assignment.course"
                                 :default-subject="defaultEmailSubject"
                                 @hide="() => $refs.contactStudentModal.hide()"
                                 @emailed="() => $refs.contactStudentModal.hide()"
                                 :can-use-snippets="canUseSnippets"
                                 class="p-3"/>
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

    <loader page-loader v-if="loadingInner"/>
    <template v-else>
        <div class="cat-wrapper"
             :class="{ hidden: selectedCat !== 'code' }">
            <component v-if="!hiddenCats.has('code')"
                       :is="$root.$isLargeWindow ? 'rs-panes' : 'div'"
                       allow-resize
                       split-to="columns"
                       :size="75"
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

                <div class="file-tree-container border rounded p-0 mt-3 mt-lg-0" slot="secondPane">
                    <file-tree :assignment="assignment"
                               :submission="submission"
                               :revision="revision" />
                </div>
            </component>
        </div>

        <div class="cat-wrapper"
             :class="{ hidden: selectedCat !== 'feedback-overview' }">
            <feedback-overview v-if="!hiddenCats.has('feedback-overview')"
                               :assignment="assignment"
                               :submission="submission"
                               :show-whitespace="showWhitespace"
                               :show-inline-feedback="selectedCat === 'feedback-overview'"
                               :can-see-feedback="canSeeUserFeedback" />
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
import 'vue-awesome/icons/envelope';
import 'vue-awesome/icons/binoculars';
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
        ...mapGetters('courses', ['assignments']),
        ...mapGetters('autotest', {
            allAutoTests: 'tests',
        }),
        ...mapGetters('fileTrees', ['getFileTree']),
        ...mapGetters('feedback', ['getFeedback']),

        courseId() {
            return Number(this.$route.params.courseId);
        },

        assignmentId() {
            return Number(this.$route.params.assignmentId);
        },

        submissionId() {
            return Number(this.$route.params.submissionId);
        },

        fileId() {
            return this.$route.params.fileId;
        },

        submission() {
            return this.storeGetSingleSubmission(this.assignmentId, this.submissionId);
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
            return this.coursePerms.can_email_students;
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

        assignment() {
            return this.assignments[this.assignmentId] || null;
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
                    name: () => {
                        let title = 'Feedback overview';
                        if (!this.feedback || !this.submission) {
                            return title;
                        }

                        const nitems = Object.values(this.feedback.user).reduce(
                            (acc, file) => Object.values(file).reduce(
                                (innerAcc, feedback) => {
                                    if (!feedback.isEmpty && feedback.replies.some(
                                        r => !r.isEmpty,
                                    )) {
                                        return innerAcc + 1;
                                    }
                                    return innerAcc;
                                },
                                acc,
                            ),
                            this.submission.comment ? 1 : 0,
                        );
                        if (nitems) {
                            title += ` <div class="ml-1 badge badge-primary">${nitems}</div>`;
                        }

                        return title;
                    },
                    enabled: true,
                },
                {
                    id: 'auto-test',
                    name: () => {
                        let title = 'AutoTest';
                        const test = this.autoTest;
                        const result = this.autoTestResult;

                        // Check that result.isFinal is exactly false, because it may be
                        // `undefined` when we haven't received the extended result yet,
                        // which would cause the CF badge to flicker on page load.
                        if (
                            test &&
                                test.results_always_visible &&
                                ((result && result.isFinal === false) || !this.canSeeGrade)
                        ) {
                            title +=
                                ' <div class="ml-1 badge badge-warning" title="Continuous Feedback">CF</div>';
                        }

                        return title;
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

        hasFeedback() {
            const fb = this.feedback;

            return !!(fb && (fb.general || Object.keys(fb.user).length));
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
            return `A comment about your submission for the assignment "${this.assignment.name}`;
        },
    },

    watch: {
        assignmentId: {
            immediate: true,
            handler() {
                this.storeLoadSubmissions(this.assignmentId);
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
                .get(`/api/v1/submissions/${this.submissionId}?type=${type}`)
                .then(({ data }) => {
                    const params = new URLSearchParams();
                    params.append('not_as_attachment', '');
                    const url = `/api/v1/files/${data.name}/${encodeURIComponent(
                        data.output_name,
                    )}?${params.toString()}`;
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

.file-tree-container {
    max-height: 100%;
    overflow: auto;

    @media @media-no-large {
        flex: 0 0 auto;
    }
}

.file-tree {
    max-height: 100%;

    @media @media-no-large {
        max-height: 15vh;
    }
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
