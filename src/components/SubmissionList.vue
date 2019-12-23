<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="submission-list d-flex flex-column">
    <b-form-fieldset>
        <b-input-group class="search-wrapper">
            <input v-model="filter"
                   class="form-control"
                   name="submissions-filter"
                   placeholder="Type to Search"
                   @keyup.enter="submit"
                   @keyup="submitDelayed"/>

            <b-input-group-append is-text
                                  class="assigned-to-me-option"
                                  v-if="canSeeOthersWork && !assigneeCheckboxDisabled"
                                  v-b-popover.bottom.hover="'Show only subbmissions assigned to me.'">
                <b-form-checkbox v-model="mineOnly"
                                 @change="submit">
                    Assigned to me
                </b-form-checkbox>
            </b-input-group-append>
        </b-input-group>
    </b-form-fieldset>

    <b-table striped
             hover
             ref="table"
             @row-clicked="gotoSubmission"
             @sort-changed="(ctx) => $nextTick(() => sortChanged(ctx))"
             :items="filteredSubmissions"
             :fields="fields"
             :current-page="currentPage"
             :sort-compare="sortSubmissions"
             :sort-by="this.$route.query.sortBy || 'user'"
             :sort-desc="!parseBool(this.$route.query.sortAsc, true)"
             class="mb-0 border-bottom submissions-table">
        <a class="invisible-link"
           href="#"
           slot="user"
           slot-scope="item"
           @click.prevent>
            <user :user="item.value"/>
            <webhook-name :submission="item.item" />
            <icon name="exclamation-triangle"
                  class="text-warning ml-1"
                  style="margin-bottom: -1px;"
                  v-b-popover.top.hover="`This user is member of the group ${quote}${usersInGroup[item.value.id].group.name}${quote}, which also created a submission.`"
                  v-if="usersInGroup[item.value.id]"/>
        </a>

        <span slot="grade" slot-scope="item" class="submission-grade">
            {{ formatGrade(item.value) || '-' }}
        </span>

        <template slot="formatted_created_at" slot-scope="item">
            {{item.value ? item.value : '-'}}
            <late-submission-icon
                :submission="item.item"
                :assignment="assignment" />
        </template>

        <span slot="assignee" slot-scope="item" class="assigned-to-grader">
            <span v-if="!canAssignGrader || graders == null">
                <user :user="item.value"
                      v-if="item.value"/>
                <span v-else>-</span>
            </span>
            <loader :scale="1"
                    v-else-if="assigneeUpdating[item.item.id]"/>
            <div v-else
                 v-b-popover.top.hover="item.item.user.is_test_student ? 'You cannot assign test students to graders.' : ''">
                <b-form-select :options="assignees"
                               :disabled="!!(item.item.user.is_test_student || usersInGroup[item.item.user.id])"
                               :value="item.value ? item.value.id : null"
                               @input="updateAssignee($event, item)"
                               @click.native.stop
                               class="user-form-select"/>
            </div>
        </span>
    </b-table>

    <div v-if="!canSeeOthersWork && this.submissions.length === 0"
         class="no-submissions-found border-bottom text-muted"
         >
        You have no submissions yet!
    </div>

    <div v-else-if="this.submissions.length === 0"
         class="no-submissions-found border-bottom text-muted"
         >
        There are no submissions yet.
    </div>

    <div v-else-if="this.submissions && this.filteredSubmissions.length === 0"
         class="no-submissions-found border-bottom text-muted"
         >
        No submissions found with the given filters.
    </div>

    <div v-if="canSeeOthersWork"
         class="submission-count border-bottom">
        Showing {{ numFilteredStudents }} out of {{ numStudents }} students.
    </div>
</div>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';
import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/exclamation-triangle';

import { waitAtLeast, formatGrade, parseBool, nameOfUser } from '@/utils';
import { filterSubmissions, sortSubmissions } from '@/utils/FilterSubmissionsManager';

import Loader from './Loader';
import User from './User';
import LateSubmissionIcon from './LateSubmissionIcon';
import WebhookName from './WebhookName';

export default {
    name: 'submission-list',

    props: {
        assignment: {
            type: Object,
            default: null,
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
            // For use in v-b-popover directives.
            quote: '"',
        };
    },

    computed: {
        ...mapGetters('user', {
            userId: 'id',
            userName: 'name',
        }),

        ...mapGetters('submissions', ['latestSubmissions', 'usersWithGroupSubmission']),

        submissions() {
            return this.latestSubmissions[this.assignment.id] || [];
        },

        usersInGroup() {
            return this.usersWithGroupSubmission[this.assignment.id] || {};
        },

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
                    let variant = null;
                    if (sub.formatted_created_at > this.assignment.formatted_deadline) {
                        variant = 'danger';
                    } else if (this.usersInGroup[sub.user.id]) {
                        variant = 'warning';
                    }

                    if (variant) {
                        return Object.assign({}, sub, {
                            _rowVariant: variant,
                        });
                    }
                    return sub;
                },
            );
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
    },

    watch: {
        filteredSubmissions: {
            immediate: true,
            handler() {
                this.$emit('filter', {
                    submissions: this.filteredSubmissions,
                });
            },
        },

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
        ...mapActions('submissions', {
            updateSubmission: 'updateSubmission',
        }),

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
                    this.updateSubmission({
                        assignmentId: this.assignment.id,
                        submissionId: submission.id,
                        submissionProps: { assignee: newAssignee },
                    });
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
        User,
        Loader,
        WebhookName,
        LateSubmissionIcon,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.submission-list {
    position: relative;
}

.submission-count,
.no-submissions-found {
    padding: 0.75rem;
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
