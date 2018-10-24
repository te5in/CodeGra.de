<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<loader center v-if="loadingPage"/>
<div class="page submission outer-container" id="submission-page" v-else>
    <b-modal id="modal_delete" title="Are you sure?" :hide-footer="true" v-if="canDeleteSubmission">
        <p style="text-align: center;">
            By deleting all information about this submission,
            including files, will be lost forever! So are you
            really sure?
        </p>
        <b-button-toolbar justify>
            <submit-button ref="deleteButton"
                           default="outline-danger"
                           @click="deleteSubmission"
                           label="Yes"/>
            <b-btn class="text-center"
                   variant="success"
                   @click="$root.$emit('bv::hide::modal', `modal_delete`)">
                No!
            </b-btn>
        </b-button-toolbar>
    </b-modal>

    <local-header :back-route="submissionsRoute"
                  back-popover="Go back to submissions list"
                  :force-extra-drawer="!$root.$isLargeWindow">
        <submission-nav-bar/>

        <component :is="!$root.$isLargeWindow ? 'template' : 'div'"
                   :slot="!$root.$isLargeWindow ? 'extra' : undefined">
            <b-input-group class="submission-header-buttons">
                <b-input-group-append v-if="canSeeFeedback">
                    <b-button class="overview-btn"
                              :variant="overviewMode ? 'primary' : 'secondary'"
                              @click="toggleOverviewMode(false)"
                              v-b-popover.bottom.hover="'Toggle overview mode'"
                              id="codeviewer-overview-toggle">
                        <icon name="binoculars"/>
                    </b-button>
                </b-input-group-append>

                <b-input-group-append>
                    <b-button class="settings-toggle"
                              v-b-popover.hover.top="'Edit settings'"
                              id="codeviewer-settings-toggle">
                        <icon name="cog"/>
                    </b-button>
                    <b-popover triggers="click"
                               class="settings-popover"
                               target="codeviewer-settings-toggle"
                               @show="beforeShowPopover"
                               container="#submission-page"
                               placement="bottom">
                        <div class="settings-content"
                             id="codeviewer-settings-content"
                             ref="settingsContent">
                            <preference-manager :file-id="(currentFile && currentFile.id) || `${submission && submission.id}-OVERVIEW`"
                                                :show-language="!(diffMode || overviewMode)"
                                                :show-context-amount="overviewMode"
                                                @context-amount="contextAmountChanged"
                                                @whitespace="whitespaceChanged"
                                                @language="languageChanged"
                                                @font-size="fontSizeChanged"/>
                        </div>
                    </b-popover>
                </b-input-group-append>

                <b-input-group-append v-if="editable || assignment.state === assignmentState.DONE">
                    <b-button id="codeviewer-general-feedback"
                              :variant="warnComment ? 'warning' : undefined"
                              v-b-popover.hover.top="`${editable ? 'Edit' : 'Show'} general feedback`">
                        <icon name="edit"/>
                    </b-button>
                    <b-popover target="codeviewer-general-feedback"
                               triggers="click"
                               container="#submission-page"
                               @show="beforeShowPopover"
                               placement="bottom">
                        <template slot="title">
                            <span v-if="submission && submission.comment_author">
                                General feedback by {{ submission.comment_author.name }}
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
                </b-input-group-append>

                <b-input-group-append v-if="gradeHistory">
                    <b-button id="codeviewer-grade-history"
                              v-b-popover.hover.top="'Grade history'">
                        <icon name="history"/>
                    </b-button>
                    <b-popover target="codeviewer-grade-history"
                               title="Grade history"
                               triggers="click"
                               container="#submission-page"
                               boundary="viewport"
                               @show="beforeShowPopover(); $refs.gradeHistory.updateHistory()"
                               placement="bottom">
                        <grade-history ref="gradeHistory"
                                       :submissionId="submission && submission.id"
                                       :isLTI="assignment && assignment.course.is_lti"/>
                    </b-popover>
                </b-input-group-append>

                <b-input-group-append>
                    <b-button v-b-popover.hover.top="'Download assignment or feedback'"
                              id="codeviewer-download-toggle">
                        <icon name="download"/>
                    </b-button>
                    <b-popover target="codeviewer-download-toggle"
                               triggers="click"
                               @show="beforeShowPopover"
                               placement="bottom">
                        <table class="table table-hover">
                            <tbody>
                                <tr @click="downloadType('zip')">
                                    <td><b>Archive</b></td>
                                </tr>
                                <tr @click="downloadType('feedback')">
                                    <td><b>Feedback</b></td>
                                </tr>
                            </tbody>
                        </table>
                    </b-popover>
                </b-input-group-append>

                <b-input-group-append v-if="canDeleteSubmission">
                    <b-btn class="text-center"
                           variant="danger"
                           v-b-popover.hover.top="'Delete submission'"
                           @click="$root.$emit('bv::show::modal',`modal_delete`)">
                        <icon name="times"/>
                    </b-btn>
                </b-input-group-append>
            </b-input-group>
        </component>
    </local-header>

    <loader center v-if="loadingInner"/>
    <div class="row justify-content-center inner-container"
         v-else
         id="submission-page-inner">
        <div class="code-and-grade"
             :class="overviewMode ?  'overview col-lg-12' : 'col-lg-9'">

            <div v-if="!fileTree || !currentFile" class="no-file">
                <loader/>
            </div>
            <b-alert show
                     class="error no-file"
                     variant="danger"
                     v-else-if="fileTree.entries.length === 0">
                No files found!
            </b-alert>
            <overview-mode v-else-if="overviewMode"
                           :assignment="assignment"
                           :submission="submission"
                           :tree="diffTree"
                           :context="contextAmount"
                           :teacher-tree="teacherTree"
                           :can-see-revision="canSeeRevision"
                           :font-size="fontSize"
                           :show-whitespace="showWhitespace"/>
            <pdf-viewer :id="currentFile.id"
                        :is-diff="diffMode"
                        v-else-if="currentFile.extension === 'pdf'"/>
            <image-viewer :id="currentFile.id"
                          :name="currentFile.name"
                          v-else-if="/^(?:gif|jpe?g|png|svg)$/.test(currentFile.extension)"/>
            <diff-viewer v-else-if="selectedRevision === 'diff' && currentFile.ids[0] !== currentFile.ids[1]"
                         :file="currentFile"
                         :font-size="fontSize"
                         :show-whitespace="showWhitespace"/>
            <code-viewer v-else
                         :assignment="assignment"
                         :submission="submission"
                         :file="currentFile"
                         :editable="editable && studentMode"
                         :tree="fileTree"
                         :font-size="fontSize"
                         :show-whitespace="showWhitespace"
                         @new-lang="languageChanged"
                         :language="selectedLanguage"/>

            <grade-viewer :assignment="assignment"
                          :submission="submission"
                          :rubric="rubric"
                          :editable="editable"
                          v-if="editable || assignment.state === assignmentState.DONE"
                          @gradeUpdated="gradeUpdated"/>
        </div>

        <div class="col-lg-3 file-tree-container" v-if="!overviewMode">
            <loader class="text-center"
                    :scale="3"
                    v-if="!fileTree"/>
            <file-tree v-else
                       class="form-control"
                       :collapsed="false"
                       :tree="fileTree"
                       :can-see-revision="canSeeRevision"
                       :revision="selectedRevision"
                       @revision="revisionChanged"/>
        </div>
    </div>
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

import { mapGetters, mapActions } from 'vuex';

import { cmpNoCase, parseBool } from '@/utils';

import {
    CodeViewer,
    DiffViewer,
    FileTree,
    GradeViewer,
    GradeHistory,
    GeneralFeedbackArea,
    ImageViewer,
    Loader,
    LocalHeader,
    PdfViewer,
    PreferenceManager,
    SubmissionNavBar,
    SubmitButton,
    Toggle,
    OverviewMode,
} from '@/components';

import * as assignmentState from '@/store/assignment-states';

import { setPageTitle } from '@/pages/title';


export default {
    name: 'submission-page',

    data() {
        return {
            studentTree: null,
            teacherTree: null,
            rubric: null,
            loadingPage: true,
            loadingInner: true,
            canDeleteSubmission: false,
            assignmentState,
            canSeeFeedback: false,
            canSeeRevision: false,
            showWhitespace: true,
            fontSize: 12,
            contextAmount: 3,
            selectedLanguage: 'Default',
            gradeHistory: true,
        };
    },

    computed: {
        ...mapGetters('user', { userId: 'id' }),
        ...mapGetters('courses', ['assignments', 'submissions']),

        studentMode() {
            return this.$route.query.revision === 'student';
        },

        courseId() {
            return Number(this.$route.params.courseId);
        },

        fileId() {
            return Number(this.$route.params.fileId);
        },

        submissionId() {
            return Number(this.$route.params.submissionId);
        },

        assignmentId() {
            return Number(this.$route.params.assignmentId);
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

        diffMode() {
            return this.selectedRevision === 'diff';
        },

        warnComment() {
            return !this.editable &&
                this.assignment.state === assignmentState.DONE &&
                this.submission.comment !== '';
        },

        overviewMode() {
            return this.canSeeFeedback && parseBool(this.$route.query.overview, false);
        },

        selectedRevision() {
            return this.$route.query.revision || 'student';
        },

        submissionsRoute() {
            return {
                name: 'assignment_submissions',
                params: {
                    courseId: this.$route.params.courseId,
                    assignmentId: this.$route.params.assignmentId,
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

        fileTree() {
            if (this.overviewMode) {
                return this.diffTree;
            }

            switch (this.selectedRevision) {
            case 'teacher':
                return this.teacherTree;
            case 'diff':
                return this.diffTree;
            case 'student':
            default:
                return this.studentTree;
            }
        },

        currentFile() {
            if (this.fileId == null || this.fileTree == null) return null;

            const file = this.searchTree(this.fileTree, this.fileId);

            if (file != null && file.extension == null) {
                file.extension = '';
                const nameparts = file.name.split('.');
                if (nameparts.length > 1) {
                    file.extension = nameparts[nameparts.length - 1];
                }
            }

            return file;
        },
    },

    watch: {
        assignment(newVal, oldVal) {
            if (newVal == null) {
                return;
            }
            if (oldVal == null || oldVal.id !== newVal.id) {
                this.$nextTick(this.updateTitle);
            }
            if (this.assignment.state === assignmentState.DONE &&
                !Object.hasOwnProperty.call(this.$route.query, 'overview')) {
                this.toggleOverviewMode(true);
            }
        },

        currentFile() {
            this.$nextTick(this.updateTitle);
        },

        async submission(newVal, oldVal) {
            if (oldVal == null || (newVal && oldVal.id === newVal.id)) {
                return;
            }

            this.loadingInner = true;

            this.setRevision('student');
            await this.getSubmissionData();

            this.loadingInner = false;
        },

        fileTree(treeTo) {
            if (treeTo == null) {
                return;
            }

            let file = null;

            if (this.fileId) {
                file = this.searchTree(treeTo, this.fileId);
                if (file == null && this.currentFile != null && this.currentFile.revision != null) {
                    file = this.searchTree(treeTo, this.currentFile.revision.id);
                }
            }

            if (file == null) {
                file = this.getFirstFile(treeTo);
            }

            if (file != null && file.id !== this.fileId) {
                const fileId = file.id || (file.ids && (file.ids[0] || file.ids[1]));
                this.$router.replace({
                    name: 'submission_file',
                    params: { fileId },
                    query: Object.assign(
                        {},
                        this.$route.query,
                        { revision: this.selectedRevision },
                    ),
                });
            }
        },

        selectedRevision(revision) {
            this.revisionChanged(revision);
        },
    },

    mounted() {
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
            this.loadSubmissions(this.assignmentId),
            this.getSubmissionData(),
        ]).then(([[
            canGrade,
            canSeeGrade,
            canDeleteSubmission,
            ownTeacher,
            editOthersWork,
            canSeeGradeHistory,
        ]]) => {
            this.editable = canGrade;
            this.canSeeFeedback = canSeeGrade ||
                (this.assignment.state === assignmentState.DONE);
            this.canDeleteSubmission = canDeleteSubmission;
            this.gradeHistory = canSeeGradeHistory;

            if (this.submission &&
                this.userId === this.submission.user.id &&
                this.assignment.state === assignmentState.DONE) {
                this.canSeeRevision = ownTeacher;
            } else {
                this.canSeeRevision = editOthersWork;
            }

            this.loadingPage = false;
            this.loadingInner = false;
        });
    },

    methods: {
        ...mapActions('courses', ['loadSubmissions', 'updateSubmission']),
        ...mapActions('courses', { storeDeleteSubmission: 'deleteSubmission' }),

        setRevision(val) {
            this.$router.push({
                name: this.$route.params.fileId ? 'submission_file' : 'submission',
                params: this.$route.params,
                query: Object.assign(
                    {},
                    this.$route.query,
                    { revision: val },
                ),
            });
        },

        updateTitle() {
            if (!this.assignment) {
                return;
            }

            let title = this.assignment.name;
            if (this.submission) {
                title += ` by ${this.submission.user.name}`;
                if (this.submission.grade) {
                    title += ` (${this.submission.grade})`;
                }
            }
            setPageTitle(title);
        },

        beforeShowPopover() {
            this.$root.$emit('bv::hide::popover');
        },

        toggleOverviewMode(forceOn = false) {
            this.$router.push({
                query: Object.assign(
                    {},
                    this.$route.query,
                    { overview: forceOn || !this.overviewMode },
                ),
            });
        },

        deleteSubmission() {
            const req = this.$http.delete(`/api/v1/submissions/${this.submissionId}`);

            this.$refs.deleteButton.submit(req.catch((err) => {
                throw err.response.data.message;
            })).then(() => {
                this.storeDeleteSubmission({
                    assignmentId: this.assignmentId,
                    submissionId: this.submissionId,
                });
                this.$router.push({
                    name: 'assignment_submissions',
                    params: {
                        courseId: this.assignment.course.id,
                        assignmentId: this.assignment.id,
                    },
                });
            });
        },

        getSubmissionData() {
            return Promise.all([
                this.getFileTrees(),
                this.getRubric(),
            ]);
        },

        getFileTrees() {
            return Promise.all([
                this.$http.get(`/api/v1/submissions/${this.submissionId}/files/`),
                this.$http.get(`/api/v1/submissions/${this.submissionId}/files/`, {
                    params: {
                        owner: 'teacher',
                    },
                }).catch(() => null),
            ]).then(([student, teacher]) => {
                this.studentTree = student.data;
                this.studentTree.isStudent = true;
                if (teacher != null) {
                    this.teacherTree = teacher.data;
                    this.teacherTree.isTeacher = true;
                    this.diffTree = this.matchFiles(this.studentTree, this.teacherTree);
                    this.diffTree.isDiff = true;
                } else {
                    this.diffTree = this.matchFiles(this.studentTree, this.studentTree);
                }
            });
        },

        matchFiles(tree1, tree2) {
            const diffTree = {
                name: tree1.name,
                entries: [],
                push(ids, name) { this.entries.push({ ids, name }); },
            };

            const lookupTree2 = tree2.entries.reduce((accum, cur) => {
                accum[cur.name] = Object.assign({}, cur, { done: false });
                return accum;
            }, {});

            tree1.entries.forEach((self) => {
                const other = lookupTree2[self.name];

                if (other == null) {
                    self.revision = null;
                    diffTree.push([self.id, null], self.name);
                    return;
                }

                other.done = true;

                if (self.id !== other.id) {
                    self.revision = other;
                    other.revision = self;
                }

                if (self.entries && other.entries) {
                    diffTree.entries.push(this.matchFiles(self, other));
                } else if (self.entries == null && other.entries == null) {
                    diffTree.push([self.id, other.id], self.name);
                } else if (self.entries) {
                    diffTree.push([null, other.id], other.name);
                    diffTree.entries.push(this.matchFiles(self, {
                        name: self.name,
                        entries: [],
                    }));
                } else if (other.entries) {
                    diffTree.push([self.id, null], self.name);
                    diffTree.entries.push(this.matchFiles({
                        name: other.name,
                        entries: [],
                    }, other));
                }
            });

            Object.values(lookupTree2).forEach((val) => {
                if (val.done) {
                    return;
                }
                if (val.entries) {
                    diffTree.entries.push(this.matchFiles({
                        name: val.name,
                        entries: [],
                    }, val));
                } else {
                    diffTree.push([null, val.id], val.name);
                }
            });

            diffTree.entries.sort((a, b) => {
                if (a.name === b.name) {
                    return a.entries ? -1 : 1;
                }
                return cmpNoCase(a.name, b.name);
            });

            delete diffTree.push;
            return diffTree;
        },

        getRubric() {
            if (!UserConfig.features.rubrics) {
                return Promise.resolve(null);
            }
            return this.$http.get(`/api/v1/submissions/${this.submissionId}/rubrics/`).then(({ data: rubric }) => {
                this.rubric = rubric;
            }, () => null);
        },

        // Returns the first file in the file tree that is not a folder
        // The file tree is searched with BFS
        getFirstFile(fileTree) {
            const queue = [fileTree];
            let candidate = null;
            let firstFound = null;

            while (queue.length > 0) {
                candidate = queue.shift();

                if (candidate.entries) {
                    queue.push(...candidate.entries);
                } else {
                    firstFound = firstFound || candidate;
                    if (!candidate.name.startsWith('.')) {
                        return candidate;
                    }
                }
            }

            // Well fuck it, lets simply return a broken file.
            return firstFound;
        },

        // Search the tree for the file with the givven id.
        searchTree(tree, id) {
            for (let i = 0; i < tree.entries.length; i += 1) {
                const child = tree.entries[i];
                if ((child.id === id || (child.revision && child.revision.id === id)) ||
                    (child.ids && (child.ids[0] === id || child.ids[1] === id))) {
                    return child;
                } else if (child.entries != null) {
                    const match = this.searchTree(child, id);
                    if (match != null) {
                        return match;
                    }
                }
            }
            return null;
        },

        downloadType(type) {
            this.$http.get(`/api/v1/submissions/${this.submissionId}?type=${type}`).then(({ data }) => {
                const params = new URLSearchParams();
                params.append('not_as_attachment', '');
                window.open(`/api/v1/files/${data.name}/${data.output_name}?${params.toString()}`);
            });
        },

        async gradeUpdated(grade) {
            await this.updateSubmission({
                assignmentId: this.assignmentId,
                submissionId: this.submission.id,
                submissionProps: { grade },
            });
            this.updateTitle();
        },

        whitespaceChanged(val) {
            this.showWhitespace = val;
        },

        languageChanged(val) {
            this.selectedLanguage = val;
        },

        contextAmountChanged(val) {
            this.contextAmount = val;
        },

        fontSizeChanged(val) {
            this.fontSize = val;
        },

        revisionChanged(val) {
            this.setRevision(val);
        },
    },

    components: {
        CodeViewer,
        DiffViewer,
        FileTree,
        GradeViewer,
        GradeHistory,
        GeneralFeedbackArea,
        ImageViewer,
        Loader,
        LocalHeader,
        PdfViewer,
        PreferenceManager,
        SubmissionNavBar,
        SubmitButton,
        Toggle,
        Icon,
        OverviewMode,
    },
};
</script>

<style lang="less" scoped>
@import "~mixins.less";

.outer-container {
    display: flex;
    flex-direction: column;
    flex: 1 1 auto;
    height: 100vh;
    max-height: 100%;
    margin-bottom: 0 !important;
}

.inner-container {
    flex: 1 1 auto;
    flex-wrap: nowrap;
    min-height: 0;

    @media @media-no-large {
        flex-direction: column;
        justify-content: start !important;
    }
}

.submission-nav-bar {
    flex: 1 1 auto;
}

.code-and-grade {
    position: relative;
    display: flex;
    flex-direction: column;
    max-height: 100%;

    @media @media-no-large {
        flex: 0 1 auto;
    }
}

.pdf-viewer {
    flex: 1 1 auto;
    min-height: 0;

    @media @media-no-large {
        flex: 1 1 100vh;
    }
}

.image-viewer {
    flex: 0 1 auto;
    min-height: 0;
}

.code-viewer,
.overview-mode,
.diff-viewer {
    overflow: auto;

    // Fixes performance issues on scrolling because the entire
    // code viewer isn't repainted anymore.
    will-change: transform;

    @media @media-no-large {
        flex: 0 1 auto;
        flex: 0 1 -webkit-max-content;
        flex: 0 1 -moz-max-content;
        flex: 0 1 max-content;
    }
}

.grade-viewer {
    flex: 0 0 auto;
}

.no-file,
.overview-mode,
.code-viewer,
.diff-viewer,
.pdf-viewer,
.image-viewer,
.file-tree-container {
    margin-bottom: 1rem;
}

.overview-mode {
    padding: 0;
}

@small-max-tree-height: 15vh;

.file-tree-container {
    max-height: 100%;

    @media @media-no-large {
        flex: 0 0 auto;
    }
}

.file-tree {
    max-height: 100%;
    overflow: auto;

    @media @media-no-large {
        max-height: @small-max-tree-height;
    }
}

.loader {
    margin-top: 1em;
}

.submission-header-buttons {
    .input-group-append:first-child button:first-of-type {
        border-top-left-radius: .25rem;
        border-bottom-left-radius: .25rem;
    }

    .input-group-append:last-child button:last-of-type {
        border-top-right-radius: .25rem;
        border-bottom-right-radius: .25rem;
    }
}

.popover .table {
    margin: -.5rem -.75rem;
    min-width: 10rem;
    text-align: left;
}
</style>

<style lang="less">
#submission-page .popover {
    max-width: 45em;
}
</style>
