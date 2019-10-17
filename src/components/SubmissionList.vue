<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="submission-list">
    <local-header always-show-extra-slot
                  ref="localHeader">
        <template slot="title" v-if="assignment && Object.keys(assignment).length">
            {{ assignment.name }}

            <small v-if="assignment.formatted_deadline">- due {{ assignment.formatted_deadline }}</small>
            <small v-else class="text-muted"><i>- No deadline</i></small>
        </template>

        <template slot="extra">
            <hr class="separator top-separator"/>

            <category-selector slot="extra"
                               :default="defaultCat"
                               v-model="selectedCat"
                               :categories="categories"/>
        </template>

        <b-input-group>
            <b-button-group>
                <b-button :to="manageAssignmentRoute"
                          variant="secondary"
                          v-if="assignment.canManage"
                          v-b-popover.bottom.hover="'Manage assignment'">
                    <icon name="gear"/>
                </b-button>
                <submit-button :wait-at-least="500"
                               :submit="submitForceLoadSubmissions"
                               v-b-popover.bottom.hover="'Reload submissions'">
                    <icon name="refresh"/>
                    <icon name="refresh" spin slot="pending-label"/>
                </submit-button>
            </b-button-group>
        </b-input-group>
    </local-header>

    <div class="cat-container border-bottom"
         :class="selectedCat"
         :style="catContainerStyle">
        <b-input-group v-if="selectedCat === 'search'"
                        class="search-wrapper">
            <input v-model="filter"
                   class="form-control"
                   placeholder="Type to Search"
                   @keyup.enter="submit"
                   @keyup="submitDelayed"/>
            <b-input-group-append is-text
                                  v-if="canSeeOthersWork && !assigneeCheckboxDisabled"
                                  v-b-popover.bottom.hover="'Show only subbmissions assigned to me.'">
                <b-form-checkbox v-model="mineOnly"
                                 @change="submit">
                    Assigned to me
                </b-form-checkbox>
            </b-input-group-append>
        </b-input-group>

        <div v-if="selectedCat === 'rubric'">
            <rubric-editor v-if="assignment.rubric != null"
                           :editable="false"
                           :default-rubric="rubric"
                           :assignment="assignment"/>
            <div no-body class="empty-text text-muted font-italic" v-else>
                There is no rubric for this assignment.
            </div>
        </div>

        <div v-if="selectedCat === 'hand-in-instructions'">
            <c-g-ignore-file v-if="assignment.cgignore"
                             :assignmentId="assignment.id"
                             :editable="false"
                             summary-mode/>
            <div no-body class="empty-text text-muted font-italic" v-else>
                There are no hand-in instructions for this assignment.
            </div>
        </div>

        <submissions-exporter v-if="selectedCat === 'export'"
                              :get-submissions="filter => filter ? filteredSubmissions : submissions"
                              :assignment-id="assignment.id"
                              :filename="exportFilename"/>
    </div>

    <b-table striped hover
             ref="table"
             @row-clicked="gotoSubmission"
             @sort-changed="(ctx) => $nextTick(() => sortChanged(ctx))"
             :items="filteredSubmissions"
             :fields="fields"
             :current-page="currentPage"
             :sort-compare="sortSubmissions"
             :sort-by="this.$route.query.sortBy || 'user'"
             :sort-desc="!parseBool(this.$route.query.sortAsc, true)"
             class="submissions-table">
        <a class="invisible-link"
           href="#"
           slot="user"
           slot-scope="item"
           @click.prevent>
            <user :user="item.value"/>
        </a>

        <template slot="grade" slot-scope="item">
            {{ formatGrade(item.value) || '-' }}
        </template>

        <template slot="formatted_created_at" slot-scope="item">
            {{item.value ? item.value : '-'}}
            <late-submission-icon :submission="item.item" :assignment="assignment" />
        </template>

        <template slot="assignee" slot-scope="item">
            <span v-if="!canAssignGrader || graders == null">
                <user :user="item.value" v-if="item.value"/>
                <span v-else>-</span>
            </span>
            <loader :scale="1" v-else-if="assigneeUpdating[item.item.id]"/>
            <div v-else
                 v-b-popover.top.hover="item.item.user.is_test_student ? 'You cannot assign test students to graders.' : ''">
                <b-form-select :options="assignees"
                               :disabled="item.item.user.is_test_student"
                               :value="item.value ? item.value.id : null"
                               @input="updateAssignee($event, item)"
                               @click.native.stop
                               class="user-form-select"/>
            </div>
        </template>
    </b-table>
    <div class="no-submissions-found"
         v-if="!canSeeOthersWork && this.submissions.length === 0">
        You have no submissions yet!
    </div>
    <div class="no-submissions-found"
         v-else-if="this.submissions.length === 0">
        There are no submissions yet.
    </div>
    <div class="no-submissions-found"
         v-else-if="this.submissions && this.filteredSubmissions.length === 0">
        No submissions found for the given filters.
    </div>

    <div v-if="canSeeOthersWork"
         class="submission-count">
        Showing {{ numFilteredStudents }} out of {{ numStudents }} students.
    </div>
</div>
</template>

<script>
import { mapGetters, mapActions } from 'vuex';
import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/gear';
import 'vue-awesome/icons/refresh';
import 'vue-awesome/icons/clock-o';

import { waitAtLeast, formatGrade, parseBool, nameOfUser } from '@/utils';
import { filterSubmissions, sortSubmissions } from '@/utils/FilterSubmissionsManager';

import SubmissionsExporter from './SubmissionsExporter';
import Loader from './Loader';
import SubmitButton from './SubmitButton';
import RubricEditor from './RubricEditor';
import LocalHeader from './LocalHeader';
import User from './User';
import CategorySelector from './CategorySelector';
import CGIgnoreFile from './CGIgnoreFile';
import LateSubmissionIcon from './LateSubmissionIcon';

export default {
    name: 'submission-list',

    props: {
        assignment: {
            type: Object,
            default: null,
        },
        submissions: {
            type: Array,
            default: [],
        },
        canDownload: {
            type: Boolean,
            default: false,
        },
        rubric: {
            default: null,
        },
        graders: {
            default: null,
            type: Array,
        },
        canSeeAssignee: {
            type: Boolean,
            required: true,
        },
        canAssignGrader: {
            type: Boolean,
            required: false,
        },
        canSeeOthersWork: {
            type: Boolean,
            required: false,
        },
    },

    data() {
        return {
            parseBool,
            mineOnly: parseBool(this.$route.query.mine, null),
            currentPage: 1,
            filter: this.$route.query.q || '',
            assignees: [],
            assigneeUpdating: [],
            selectedCat: '',
        };
    },

    computed: {
        ...mapGetters('user', {
            userId: 'id',
            userName: 'name',
        }),

        fields() {
            const fields = [
                {
                    key: 'user',
                    label: 'User',
                    sortable: true,
                },
                {
                    key: 'grade',
                    label: 'Grade',
                    sortable: true,
                },
                {
                    key: 'formatted_created_at',
                    label: 'Created at',
                    sortable: true,
                },
            ];
            if (this.canSeeAssignee) {
                fields.push({
                    key: 'assignee',
                    label: 'Assigned to',
                    sortable: true,
                });
            }
            return fields;
        },

        categories() {
            return [
                {
                    id: 'search',
                    name: 'Search',
                    enabled: true,
                },
                {
                    id: 'rubric',
                    name: 'Rubric',
                    enabled: true,
                },
                {
                    id: 'hand-in-instructions',
                    name: 'Hand-in instructions',
                    enabled: true,
                },
                {
                    id: 'export',
                    name: 'Export',
                    enabled: this.canDownload,
                },
            ];
        },

        defaultCat() {
            if (!this.canSeeOthersWork && this.assignment.rubric != null) {
                return 'rubric';
            } else if (!this.canSeeOthersWork && this.assignment.cgignore) {
                return 'hand-in-requirements';
            } else {
                return 'search';
            }
        },

        exportFilename() {
            return this.assignment
                ? `${this.assignment.course.name}-${this.assignment.name}.csv`
                : null;
        },

        filteredSubmissions() {
            // WARNING: We need to access all, do not change!
            if (
                [this.submissions, this.mineOnly, this.userId, this.filter].indexOf(undefined) !==
                -1
            ) {
                return [];
            }

            return filterSubmissions(this.submissions, this.mineOnly, this.userId, this.filter).map(
                sub => {
                    if (sub.formatted_created_at > this.assignment.formatted_deadline) {
                        return Object.assign({}, sub, {
                            _rowVariant: 'danger',
                        });
                    }
                    return sub;
                },
            );
        },

        manageAssignmentRoute() {
            return {
                name: 'manage_assignment',
                params: {
                    courseId: this.assignment.course.id,
                    assignmentId: this.assignment.id,
                },
            };
        },

        numStudents() {
            return new Set(this.submissions.map(sub => nameOfUser(sub.user))).size;
        },

        numFilteredStudents() {
            return new Set(this.filteredSubmissions.map(sub => nameOfUser(sub.user))).size;
        },

        assigneeCheckboxDisabled() {
            if (this.submissions == null) {
                return true;
            }

            return !this.submissions.find(
                s => this.$utils.getProps(s, null, 'assignee', 'id') === this.userId,
            );
        },

        catContainerStyle() {
            // We get the window width (but we don't need it for anything) as we want this property
            // to be recomputed when then window size changes, because the clientHeight of the
            // LocalHeader may change then.
            // eslint-disable-next-line
            const winWidth = this.$root.$windowWidth;

            switch (this.selectedCat) {
                case 'search':
                    return {
                        position: 'sticky',
                        top: `${this.$utils.getProps(
                            this.$refs,
                            0,
                            'localHeader',
                            '$el',
                            'clientHeight',
                        )}px`,
                    };
                default:
                    return {};
            }
        },
    },

    watch: {
        graders(graders) {
            if (graders == null) return;

            this.updateGraders(graders);
        },

        assigneeCheckboxDisabled: {
            immediate: true,
            handler(newVal) {
                if (newVal && this.mineOnly) {
                    this.mineOnly = false;
                    this.submit();
                }
            },
        },
    },

    mounted() {
        if (this.graders) {
            this.updateGraders(this.graders);
        }
        if (this.mineOnly == null) {
            this.mineOnly = this.submissions.some(
                s => s.user.id === this.userId || (s.assignee && s.assignee.id === this.userId),
            );
        }
        if (!this.mineOnly) {
            this.submit();
        }
    },

    methods: {
        ...mapActions('submissions', ['forceLoadSubmissions']),

        submitForceLoadSubmissions() {
            return this.forceLoadSubmissions(this.assignment.id);
        },

        updateGraders(graders) {
            const assignees = graders.map(ass => ({
                value: ass.id,
                text: nameOfUser(ass),
                data: ass,
            }));
            assignees.unshift({ value: null, text: '-', data: null });
            this.assignees = assignees;
        },

        sortChanged(context) {
            this.$router.replace({
                query: Object.assign({}, this.$route.query, {
                    sortBy: context.sortBy,
                    sortAsc: !context.sortDesc,
                }),
                hash: this.$route.hash,
            });
        },

        gotoSubmission(submission) {
            this.submit();

            this.$router.push({
                name: 'submission',
                params: { submissionId: submission.id },
                query: {
                    mine: this.mineOnly == null ? undefined : this.mineOnly,
                    search: this.filter || undefined,
                    // Fuck you bootstrapVue (sortDesc should've been sortAsc)
                    sortBy: this.$refs.table.sortBy,
                    sortAsc: !this.$refs.table.sortDesc,
                },
            });
        },

        submitDelayed() {
            if (this.submitTimeout != null) {
                clearTimeout(this.submitTimeout);
            }

            this.submitTimeout = setTimeout(() => {
                this.submitTimeout = null;
                this.submit();
            }, 200);
        },

        async submit() {
            await this.$nextTick();

            this.$router.replace({
                query: Object.assign({}, this.$route.query, {
                    mine: this.mineOnly,
                    q: this.filter || undefined,
                }),
                hash: this.$route.hash,
            });
        },

        updateAssignee(newId, { item: submission }) {
            const oldId = submission.assignee ? submission.assignee.id : null;
            if (oldId === newId) {
                return;
            }

            this.$set(this.assigneeUpdating, submission.id, true);

            let res;
            if (newId != null) {
                res = this.$http.patch(`/api/v1/submissions/${submission.id}/grader`, {
                    user_id: newId,
                });
            } else {
                res = this.$http.delete(`/api/v1/submissions/${submission.id}/grader`);
            }

            waitAtLeast(250, res).then(
                () => {
                    this.$set(this.assigneeUpdating, submission.id, false);
                    let newAssignee;
                    for (let i = 0; i < this.assignees.length; i += 1) {
                        if (this.assignees[i].data && this.assignees[i].data.id === newId) {
                            newAssignee = this.assignees[i].data;
                            break;
                        }
                    }
                    this.$emit('assigneeUpdated', submission, newAssignee);
                },
                ({ response }) => {
                    // TODO: visual feedback
                    // eslint-disable-next-line
                    console.log(response);
                },
            );
        },

        formatGrade,
        sortSubmissions,
    },

    components: {
        Icon,
        Loader,
        SubmitButton,
        RubricEditor,
        SubmissionsExporter,
        LocalHeader,
        User,
        CategorySelector,
        CGIgnoreFile,
        LateSubmissionIcon,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.submission-list {
    position: relative;
    margin-bottom: 1rem;
}

.separator.top-separator {
    margin: 0.5rem 0;
}

.cat-container {
    margin: -1rem -15px 1rem;
    padding: 1rem;
    background-color: white;
    z-index: 100;

    #app.dark & {
        background-color: @color-primary;
    }
}

.empty-text {
    padding: 0.375rem 0.75rem;
    border: 1px solid transparent;
}

.submission-count,
.no-submissions-found {
    padding: 0.75rem;
    border: 1px solid #dee2e6;
    border-right-width: 0;
    border-left-width: 0;

    #app.dark & {
        border-color: @color-primary-darker;
    }
}

.no-submissions-found {
    color: @text-color-muted;
}

.user-form-select {
    max-width: 20em;
    margin: -0.35rem 0;
    cursor: pointer;
    &[disabled] {
        cursor: not-allowed;
    }
}
</style>

<style lang="less">
@import '~mixins.less';

.submissions-table {
    margin-bottom: 0;

    td,
    th {
        vertical-align: middle;

        // student
        &:nth-child(1) {
            width: 30em;
        }

        // grade
        // created at
        // assignee
        &:nth-child(2),
        &:nth-child(3),
        &:nth-child(4) {
            width: 1px;
            white-space: nowrap;
        }

        .loader {
            padding: 0.33rem;
        }
    }
}

.submission-list .search-wrapper {
    #app.dark & .input-group-append .input-group-text {
        background-color: @color-primary-darkest !important;
    }
}
</style>
