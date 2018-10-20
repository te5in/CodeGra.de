<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="submission-list">
    <local-header>
        <b-input-group class="search-wrapper">
            <input v-model="filter"
                   class="form-control"
                   placeholder="Type to Search"
                   @keyup.enter="submit"
                   @keyup="submitDelayed"/>

            <b-input-group-append v-if="latest.length !== submissions.length" is-text>
                <b-form-checkbox v-model="latestOnly" @change="submit">
                    Latest only
                </b-form-checkbox>
            </b-input-group-append>

            <b-input-group-append v-if="assigneeFilter" is-text>
                <b-form-checkbox v-model="mineOnly" @change="submit">
                    Assigned to me
                </b-form-checkbox>
            </b-input-group-append>
        </b-input-group>

        <b-input-group>
            <b-button-group>
                <b-button :to="manageAssignmentRoute"
                          variant="secondary"
                          v-if="assignment.canManage"
                          v-b-popover.bottom.hover="'Manage assignment'">
                    <icon name="gear"/>
                </b-button>
                <submit-button @click="submitForceLoadSubmissions"
                               variant="secondary"
                               ref="refreshButton"
                               :label="false"
                               v-b-popover.bottom.hover="'Reload submissions'">
                    <icon name="refresh"/>
                    <icon name="refresh" spin slot="pending"/>
                </submit-button>
            </b-button-group>
        </b-input-group>

        <div slot="extra" class="clearfix">
            <div id="show-rubric-button-wrapper"
                 style="float: right;">
                <submit-button label="Show Rubric"
                               @click="showRubricModal = !showRubricModal"
                               default="secondary"
                               :disabled="!rubric"/>
            </div>
            <b-popover target="show-rubric-button-wrapper"
                       content="There is no rubric for this assignment"
                       triggers="hover"
                       placement="bottom"
                       v-if="!rubric"/>
            <submissions-exporter v-if="canDownload && submissions.length"
                                  :get-submissions="filter => filter ? filteredSubmissions : submissions"
                                  :assignment-id="assignment.id"
                                  :filename="exportFilename">
                Export feedback
            </submissions-exporter>
        </div>
    </local-header>

    <b-modal v-if="rubric"
             id="rubric-modal"
             class="rubric-modal"
             v-model="showRubricModal"
             :hide-footer="true"
             :hide-header="true">
        <rubric-editor :editable="false"
                       :defaultRubric="rubric"
                       :assignment="assignment">
            <b-button variant="primary"
                      @click="$root.$emit('bv::hide::modal','rubric-modal')">
                Close
            </b-button>
        </rubric-editor>
    </b-modal>


    <b-table striped hover
             ref="table"
             @row-clicked="gotoSubmission"
             @sort-changed="(ctx) => $nextTick(() => sortChanged(ctx))"
             :items="filteredSubmissions"
             :fields="fields"
             :current-page="currentPage"
             :sort-compare="sortSubmissions"
             :show-empty="true"
             :sort-by="this.$route.query.sortBy || 'user'"
             :sort-desc="!parseBool(this.$route.query.sortAsc, true)"
             class="submissions-table">
        <a class="invisible-link"
           href="#"
           slot="user"
           slot-scope="item"
           @click.prevent>
            {{item.value.name ? item.value.name : '-'}}
        </a>
        <template slot="grade" slot-scope="item">
            {{formatGrade(item.value) || '-'}}
        </template>
        <template slot="created_at" slot-scope="item">
            {{item.value ? item.value : '-'}}
        </template>
        <template slot="assignee" slot-scope="item">
            <span v-if="!canChangeAssignee">
                {{ item.value ? item.value.name : '-' }}
            </span>
            <loader :scale="1" v-else-if="assigneeUpdating[item.item.id]"/>
            <b-form-select
                :options="assignees"
                :value="item.value ? item.value.id : null"
                @input="updateAssignee($event, item)"
                @click.native.stop
                style="max-width: 20em;"
                v-else/>
        </template>
    </b-table>
</div>
</template>

<script>
import { mapGetters, mapActions } from 'vuex';
import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/gear';
import 'vue-awesome/icons/refresh';

import { formatGrade, parseBool, waitAtLeast } from '@/utils';
import { filterSubmissions, sortSubmissions } from '@/utils/FilterSubmissionsManager';

import * as assignmentState from '@/store/assignment-states';
import SubmissionsExporter from './SubmissionsExporter';
import Loader from './Loader';
import SubmitButton from './SubmitButton';
import RubricEditor from './RubricEditor';
import LocalHeader from './LocalHeader';

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
    },

    data() {
        return {
            parseBool,
            showRubricModal: false,
            latestOnly: parseBool(this.$route.query.latest, true),
            mineOnly: parseBool(this.$route.query.mine, true),
            currentPage: 1,
            filter: this.$route.query.q || '',
            latest: this.getLatest(this.submissions),
            assigneeFilter: false,
            assignees: [],
            assigneeUpdating: [],
        };
    },

    computed: {
        ...mapGetters('user', {
            userId: 'id',
            userName: 'name',
        }),

        canChangeAssignee() {
            return this.graders != null;
        },

        fields() {
            const fields = [
                {
                    key: 'user',
                    label: 'User',
                    sortable: true,
                }, {
                    key: 'grade',
                    label: 'Grade',
                    sortable: true,
                }, {
                    key: 'created_at',
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

        exportFilename() {
            return this.assignment ? `${this.assignment.course.name}-${this.assignment.name}.csv` : null;
        },

        filteredSubmissions() {
            // WARNING: We need to access all, do not change!
            if ([
                this.submissions,
                this.latestOnly,
                this.mineOnly,
                this.userId,
                this.filter,
            ].indexOf(undefined) !== -1) {
                return [];
            }

            return filterSubmissions(
                this.submissions,
                this.latestOnly,
                this.mineOnly,
                this.userId,
                this.filter,
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
    },

    watch: {
        submissions(submissions) {
            this.latest = this.getLatest(submissions);
        },

        graders(graders) {
            if (graders == null) return;

            this.updateGraders(graders);
        },
    },

    mounted() {
        this.updateAssigneeFilter();
        if (this.graders) {
            this.updateGraders(this.graders);
        }
    },

    methods: {
        ...mapActions('courses', ['forceLoadSubmissions']),

        submitForceLoadSubmissions() {
            const req = waitAtLeast(500, this.forceLoadSubmissions(this.assignment.id).catch(
                (err) => {
                    throw err.response.data.message;
                },
            ));
            this.$refs.refreshButton.submit(req);
        },

        updateAssigneeFilter() {
            this.assigneeFilter = this.submissions.some(
                s => s.assignee && s.assignee.id === this.userId,
            );
        },

        updateGraders(graders) {
            const assignees = graders.map(ass =>
                ({ value: ass.id, text: ass.name, data: ass }));
            assignees.unshift({ value: null, text: '-', data: null });
            this.assignees = assignees;
        },

        getLatest(submissions) {
            const latest = {};
            submissions.forEach((item) => {
                if (!latest[item.user.id]) {
                    latest[item.user.id] = item.id;
                }
            });
            return latest;
        },

        sortChanged(context) {
            this.$router.replace({
                query: Object.assign(
                    {},
                    this.$route.query,
                    { sortBy: context.sortBy, sortAsc: !context.sortDesc },
                ),
            });
        },

        gotoSubmission(submission) {
            this.submit();

            this.$router.push({
                name: 'submission',
                params: { submissionId: submission.id },
                query: {
                    mine: this.mineOnly == null ? undefined : this.mineOnly,
                    latest: this.latestOnly == null ? undefined : this.latestOnly,
                    search: this.filter || undefined,
                    // Fuck you bootstrapVue (sortDesc should've been sortAsc)
                    sortBy: this.$refs.table.sortBy,
                    sortAsc: !this.$refs.table.sortDesc,
                    overview: this.assignment.state === assignmentState.DONE &&
                        submission.grade != null,
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
                    latest: this.latestOnly,
                    mine: this.mineOnly,
                    q: this.filter || undefined,
                }),
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

            res.then(() => {
                this.$set(this.assigneeUpdating, submission.id, false);
                let newAssignee;
                for (let i = 0; i < this.assignees.length; i += 1) {
                    if (this.assignees[i].data && this.assignees[i].data.id === newId) {
                        newAssignee = this.assignees[i].data;
                        break;
                    }
                }
                this.$emit('assigneeUpdated', submission, newAssignee);
                this.updateAssigneeFilter();
            }, ({ response }) => {
                // TODO: visual feedback
                // eslint-disable-next-line
                console.log(response);
            });
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
    },
};
</script>

<style lang="less">
@import "~mixins.less";

.submissions-table {
    padding-top: 5em;
    content-sizing: content-box;
    td, th {
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
    }
}

.submissions-table td:last-child {
    padding-top: 0.3rem;
    padding-bottom: 0.3rem;
}

.submissions-table td .loader {
    padding: 0.7rem;
}

.submission-list .modal-dialog.modal-md {
    max-width: 1550px;
    width: 100%;
}

.rubric-modal .modal-body {
    padding: 0;

    #app.dark & .nav-tabs {
        background-color: @color-primary-darker;
    }
}

.submission-list .search-wrapper {
    flex: 1;

    #app.dark & .input-group-append .input-group-text {
        background-color: @color-primary-darkest !important;
    }
}
</style>
