<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<loader center v-if="loadingPage"/>
<div class="page submission outer-container" id="submission-page" v-else>
    <b-modal id="modal_delete" title="Are you sure?" hide-footer v-if="canDeleteSubmission">
        <p style="text-align: center;">
            By deleting all information about this submission,
            including files, will be lost forever! So are you
            really sure?
        </p>
        <b-button-toolbar justify>
            <submit-button label="Yes"
                           variant="outline-danger"
                           :submit="deleteSubmission"
                           @after-success="afterDeleteSubmission"/>
            <b-btn class="text-center"
                   variant="success"
                   @click="$root.$emit('bv::hide::modal', `modal_delete`)">
                No!
            </b-btn>
        </b-button-toolbar>
    </b-modal>

    <local-header :back-route="submissionsRoute"
                  back-popover="Go back to submissions list"
                  always-show-extra-slot
                  :force-extra-drawer="!$root.$isLargeWindow">
        <submission-nav-bar/>

        <b-button-group class="submission-header-buttons">
            <b-button class="settings-toggle"
                      v-b-popover.hover.top="'Settings'"
                      id="codeviewer-settings-toggle">
                <icon name="cog"/>

                <b-popover triggers="click"
                           class="settings-popover"
                           target="codeviewer-settings-toggle"
                           @show="beforeShowPopover"
                           container="#submission-page"
                           placement="bottom">
                    <div class="settings-content"
                         id="codeviewer-settings-content"
                         ref="settingsContent">
                        <preference-manager :file-id="prefFileId"
                                            :show-context-amount="selectedCat === 'feedback-overview' || selectedCat === 'teacher-diff'"
                                            :show-language="selectedCat === 'code'"
                                            @whitespace="whitespaceChanged"
                                            @language="languageChanged"/>
                    </div>
                </b-popover>
            </b-button>

            <b-button v-if="editable"
                      id="codeviewer-general-feedback"
                      v-b-popover.hover.top="`Edit general feedback`">
                <icon name="edit"/>

                <b-popover target="codeviewer-general-feedback"
                           triggers="click"
                           container="#submission-page"
                           @show="beforeShowPopover"
                           placement="bottom">
                    <template slot="title">
                        <span v-if="submission && submission.comment_author">
                            General feedback by <user :user="submission.comment_author"/>
                        </span>
                        <span v-else>
                            General feedback
                        </span>
                    </template>
                    <general-feedback-area style="width: 35em;"
                                           :assignment="assignment"
                                           :submission="submission"
                                           :editable="editable"/>
                </b-popover>
            </b-button>

            <b-button v-if="canSeeGradeHistory"
                      id="codeviewer-grade-history"
                      v-b-popover.hover.top="'Grade history'">
                <icon name="history"/>

                <b-popover target="codeviewer-grade-history"
                           title="Grade history"
                           triggers="click"
                           container="#submission-page"
                           boundary="viewport"
                           @show="beforeShowPopover(); $refs.gradeHistory.updateHistory()"
                           placement="bottom">
                    <grade-history ref="gradeHistory"
                                   :submission-id="submission && submission.id"
                                   :isLTI="assignment && assignment.course.is_lti"/>
                </b-popover>
            </b-button>

            <b-button v-b-popover.hover.top="'Download assignment or feedback'"
                      id="codeviewer-download-toggle">
                <icon name="download"/>

                <b-popover target="codeviewer-download-toggle"
                           triggers="click"
                           @show="beforeShowPopover"
                           placement="bottom">
                    <table class="table table-hover">
                        <tbody>
                            <tr @click="downloadType('zip')">
                                <td><b>Archive</b></td>
                            </tr>
                            <tr v-if="canSeeFeedback"
                                @click="downloadType('feedback')">
                                <td><b>Feedback</b></td>
                            </tr>
                        </tbody>
                    </table>
                </b-popover>
            </b-button>

            <b-btn v-if="canDeleteSubmission"
                   variant="danger"
                   v-b-popover.hover.top="'Delete submission'"
                   @click="$root.$emit('bv::show::modal',`modal_delete`)">
                <icon name="times"/>
            </b-btn>
        </b-button-group>

        <template slot="extra">
            <hr class="mt-2 mb-1" />

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
                             :editable="canGiveLineFeedback"
                             :can-use-snippets="canUseSnippets"
                             :show-whitespace="showWhitespace"
                             :language="selectedLanguage"
                             @language="languageChanged" />

                <div class="file-tree-container form-control p-0 mt-3 mt-lg-0" slot="secondPane">
                    <file-tree :assignment="assignment"
                               :submission="submission"
                               :can-see-revision="canSeeRevision"
                               :revision="revision"
                               @revision="setRevision" />
                </div>
            </component>
        </div>

        <div class="cat-wrapper"
             :class="{ hidden: selectedCat !== 'feedback-overview' }">
            <feedback-overview v-if="!hiddenCats.has('feedback-overview')"
                               :assignment="assignment"
                               :submission="submission"
                               :show-whitespace="showWhitespace"
                               :can-see-feedback="canSeeFeedback" />
        </div>

        <div class="cat-wrapper"
             :class="{ hidden: selectedCat !== 'teacher-diff' }">
            <diff-overview v-if="!hiddenCats.has('teacher-diff')"
                           :assignment="assignment"
                           :submission="submission"
                           :show-whitespace="showWhitespace"/>
        </div>

        <div class="cat-wrapper"
             :class="{ hidden: selectedCat !== 'auto-test' }">
            <div class="cat-scroller border rounded">
                <auto-test v-if="!hiddenCats.has('auto-test')"
                           :assignment="assignment"
                           :submission-id="submissionId" />
            </div>
        </div>
    </template>

    <grade-viewer :assignment="assignment"
                  :submission="submission"
                  :editable="editable"
                  :rubric-start-open="canSeeFeedback"
                  v-if="!loadingInner && (editable || assignment.state === assignmentState.DONE)"
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

export default {
    name: 'submission-page',

    data() {
        return {
            assignmentState,

            canDeleteSubmission: false,
            canSeeFeedback: false,
            canSeeRevision: false,
            canSeeGradeHistory: true,
            editable: false,
            canUseSnippets: false,

            selectedCat: '',
            hiddenCats: new Set(),

            showWhitespace: true,
            selectedLanguage: 'Default',
            currentFile: null,
        };
    },

    computed: {
        ...mapGetters('pref', ['contextAmount', 'fontSize']),
        ...mapGetters('user', { userId: 'id' }),
        ...mapGetters('courses', ['assignments']),

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
            const fileId = Number(this.$route.params.fileId);
            return Number.isNaN(fileId) ? null : fileId;
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

        submissions() {
            return (this.assignment && this.assignment.submissions) || [];
        },

        submission() {
            return this.submissions.find(sub => sub.id === this.submissionId) || null;
        },

        fileTree() {
            return this.submission && this.submission.fileTree;
        },

        feedback() {
            return this.submission && this.submission.feedback;
        },

        loadingPage() {
            return !(this.assignment && this.assignment.submissions);
        },

        loadingInner() {
            const canSeeFeedback = this.canSeeFeedback;
            const feedback = this.feedback;
            const fileTree = this.fileTree;
            const currentFile = this.currentFile;

            return (canSeeFeedback && !feedback) || !fileTree || !currentFile;
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
                        if (!this.feedback) {
                            return title;
                        }

                        const nitems = Object.values(this.feedback.user).reduce(
                            (acc, file) => acc + Object.keys(file).length,
                            this.feedback.general ? 1 : 0,
                        );
                        if (nitems) {
                            title += ` <div class="ml-1 badge badge-primary" style="font-size: 1em;">${nitems}</div>`;
                        }

                        return title;
                    },
                    enabled: true,
                },
                {
                    id: 'auto-test',
                    name: 'AutoTest',
                    enabled: this.assignment && this.assignment.auto_test_id != null,
                },
                {
                    id: 'teacher-diff',
                    name: 'Teacher diff',
                    enabled: this.fileTree && this.fileTree.hasRevision(this.fileTree.student),
                },
            ];
        },

        defaultCat() {
            const canSeeFeedback = this.canSeeFeedback;
            const hasGrade = this.submission.grade != null;

            return canSeeFeedback && hasGrade ? 'feedback-overview' : 'code';
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
                },
            };
        },

        canGiveLineFeedback() {
            return this.editable && this.revision === 'student';
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
    },

    watch: {
        courseId: {
            immediate: true,
            handler() {
                this.loadPermissions();
            },
        },

        assignmentId: {
            immediate: true,
            handler() {
                this.storeLoadSubmissions(this.assignmentId);
            },
        },

        submissionId: {
            immediate: true,
            handler() {
                this.loadData();
            },
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
                this.openFirstFile();
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
        ...mapActions('courses', {
            storeLoadSubmissions: 'loadSubmissions',
            storeUpdateSubmission: 'updateSubmission',
            storeDeleteSubmission: 'deleteSubmission',
            storeLoadFileTree: 'loadSubmissionFileTree',
            storeLoadFeedback: 'loadSubmissionFeedback',
        }),

        loadPermissions() {
            Promise.all([
                this.$hasPermission(
                    [
                        'can_grade_work',
                        'can_see_grade_before_open',
                        'can_delete_submission',
                        'can_view_own_teacher_files',
                        'can_edit_others_work',
                        'can_see_grade_history',
                    ],
                    this.courseId,
                ),
                this.$hasPermission('can_use_snippets'),
            ]).then(
                ([
                    [
                        canGrade,
                        canSeeGrade,
                        canDeleteSubmission,
                        ownTeacher,
                        editOthersWork,
                        canSeeGradeHistory,
                    ],
                    canUseSnippets,
                ]) => {
                    this.editable = canGrade;
                    this.canSeeFeedback =
                        canSeeGrade || this.assignment.state === assignmentState.DONE;
                    this.canDeleteSubmission = canDeleteSubmission;
                    this.canSeeGradeHistory = canSeeGradeHistory;

                    this.canUseSnippets = canUseSnippets;

                    if (
                        this.submission &&
                        this.userId === this.submission.user.id &&
                        this.assignment.state === assignmentState.DONE
                    ) {
                        this.canSeeRevision = ownTeacher;
                    } else {
                        this.canSeeRevision = editOthersWork;
                    }
                },
            );
        },

        loadData() {
            this.setRevision('student', 'replace');
            this.currentFile = null;
            this.showWhitespace = true;

            this.hiddenCats = new Set(
                this.categories.map(c => c.id).filter(c => c.enabled && c !== this.selectedCat),
            );

            return Promise.all([
                this.storeLoadFileTree({
                    assignmentId: this.assignmentId,
                    submissionId: this.submissionId,
                }),
                this.storeLoadFeedback({
                    assignmentId: this.assignmentId,
                    submissionId: this.submissionId,
                }),
            ]).then(this.openFirstFile);
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
            if (this.fileTree) {
                this.currentFile = this.fileTree.search(this.revision, this.fileId);
            }
        },

        setRevision(val, method = 'push') {
            const route = this.$utils.deepExtend({}, this.$route, {
                query: { revision: val },
            });
            this.$router[method](route);
        },

        beforeShowPopover() {
            this.$root.$emit('bv::hide::popover');
        },

        deleteSubmission() {
            return this.$http.delete(`/api/v1/submissions/${this.submissionId}`);
        },

        afterDeleteSubmission() {
            this.storeDeleteSubmission({
                assignmentId: this.assignmentId,
                submissionId: this.submissionId,
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
                    window.open(
                        `/api/v1/files/${data.name}/${data.output_name}?${params.toString()}`,
                    );
                });
        },

        languageChanged(val) {
            this.selectedLanguage = val;
        },

        whitespaceChanged(val) {
            this.showWhitespace = val;
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
    transition: opacity 0.25s ease-out;
    overflow: hidden;

    &.hidden {
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

.popover .table {
    margin: -0.5rem -0.75rem;
    min-width: 10rem;
    text-align: left;
}
</style>

<style lang="less">
@import '~mixins.less';

#submission-page {
    .popover {
        max-width: 45em;
    }

    .pane-rs {
        position: relative;
    }

    .Resizer {
        z-index: 0;
    }

    .Resizer.columns {
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
        }

        &:before {
            transform: translate(-2px, -4px);
        }

        &:after {
            transform: translate(-2px, +1px);
        }
    }
}
</style>
