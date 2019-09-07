<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<b-card no-body class="auto-test-run">
    <collapse v-model="resultsCollapsed">
        <b-card-header
            slot="handle"
            class="d-flex justify-content-between align-items-center"
            :class="{ 'py-1': editable }">
            <span class="toggle flex-grow-1">
                <icon name="chevron-down" :scale="0.75" />
                Results
            </span>

            <b-button-toolbar>
                <auto-test-state btn no-timer :result="run" />

                <div v-if="editable"
                     v-b-popover.hover.top="deleteResultsPopover">
                    <submit-button variant="danger"
                                   class="ml-1"
                                   :label="run.finished ? 'Delete' : 'Stop'"
                                   confirm="Are you sure you want to delete the results?"
                                   :disabled="!permissions.can_delete_autotest_run"
                                   :submit="deleteResults"
                                   @success="afterDeleteResults"
                                   @after-success="afterAfterDeleteResults" />
                </div>
            </b-button-toolbar>
        </b-card-header>

        <table class="table table-striped results-table"
               :id="tableId"
               :class="{ 'table-hover': run.results.length > 0 }">
            <thead>
                <tr>
                    <th class="name">Name</th>
                    <th class="score">Score</th>
                    <th class="state">State</th>
                </tr>
            </thead>

            <tbody v-if="run.results.length > 0">
                <tr v-if="submissionsLoading">
                    <td colspan="3"><loader :scale="1" /></td>
                </tr>
                <template v-else>
                    <tr v-for="resultOffset in perPage"
                        v-if="getResult(resultOffset) != null"
                        :key="`result-${getResult(resultOffset).id}-submission-${getResult(resultOffset).submissionId}`"
                        @click="openResult(getResult(resultOffset))">
                        <td class="name">
                            {{ $utils.nameOfUser(submissions[getResult(resultOffset).submissionId].user) }}
                        </td>
                        <td class="score">
                            <icon v-if="submissions[getResult(resultOffset).submissionId].grade_overridden"
                                v-b-popover.top.hover="'This submission\'s calculated grade has been manually overridden'"
                                name="exclamation-triangle"/>
                            {{ $utils.toMaxNDecimals($utils.getProps(getResult(resultOffset), '-', 'pointsAchieved'), 2) }} /
                            {{ $utils.toMaxNDecimals(autoTest.pointsPossible, 2) }}
                        </td>
                        <td class="state">
                            <auto-test-state :result="getResult(resultOffset)" show-icon />
                        </td>
                    </tr>
                </template>
            </tbody>
            <tbody v-else>
                <tr>
                    <td colspan="3">No results</td>
                </tr>
            </tbody>
        </table>

        <b-pagination
            class="pagination mt-3"
            v-if="run.results.length > 0 && run.results.length > perPage"
            v-model="currentPage"
            :limit="10"
            :total-rows="run.results.length"
            :per-page="perPage"
            :aria-controls="tableId"/>
    </collapse>
</b-card>
</template>

<script>
import { mapActions } from 'vuex';

import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/chevron-down';
import 'vue-awesome/icons/exclamation-triangle';

import Collapse from './Collapse';
import SubmitButton from './SubmitButton';
import AutoTestState from './AutoTestState';
import Loader from './Loader';

export default {
    name: 'auto-test-run',

    props: {
        assignment: {
            type: Object,
            required: true,
        },

        autoTest: {
            type: Object,
            required: true,
        },

        run: {
            type: Object,
            required: true,
        },

        editable: {
            type: Boolean,
            default: false,
        },
    },

    data() {
        const id = this.$utils.getUniqueId();

        return {
            resultsCollapsed: false,
            resultsCollapseId: `auto-test-results-collapse-${id}`,
            submissions: {},
            submissionsLoading: true,
            currentPage: 1,
            perPage: 15,
            tableId: `auto-test-results-table-${this.$utils.getUniqueId()}`,
        };
    },

    computed: {
        permissions() {
            return this.$utils.getProps(this, {}, 'assignment', 'course', 'permissions');
        },

        deleteResultsPopover() {
            if (!this.permissions.can_delete_autotest_run) {
                return 'You do not have permission to delete AutoTest results.';
            } else {
                return '';
            }
        },

        submissionIds() {
            return this.$utils.getProps(this.run, [], 'results').map(res => res.submissionId);
        },

        runId() {
            return this.$utils.getProps(this.run, null, 'id');
        },
    },

    watch: {
        runId() {
            this.currentPage = 1;
        },

        submissionIds: {
            immediate: true,
            handler() {
                this.submissionsLoading = true;
                this.submissions = {};
                const ids = this.submissionIds;

                this.storeLoadGivenSubmissions({
                    assignmentId: this.assignment.id,
                    submissionIds: ids,
                }).then(subs => {
                    if (this.submissionIds === ids) {
                        subs.forEach(sub => {
                            this.submissions[sub.id] = sub;
                        });
                        this.submissionsLoading = false;
                    }
                });
            },
        },
    },

    methods: {
        ...mapActions('submissions', {
            storeLoadGivenSubmissions: 'loadGivenSubmissions',
        }),

        ...mapActions('autotest', {
            storeDeleteAutoTestResults: 'deleteAutoTestResults',
        }),

        getResult(resultOffset) {
            // We need to substract one here as looping over an integer in vue
            // returns numbers that are one-indexed.
            const index = resultOffset - 1 + this.perPage * (this.currentPage - 1);
            const results = this.$utils.getProps(this.run, [], 'results');
            if (index >= results.length) {
                return null;
            }
            return results[index];
        },

        deleteResults() {
            return this.storeDeleteAutoTestResults({
                autoTestId: this.autoTest.id,
                runId: this.run.id,
            });
        },

        afterDeleteResults() {
            this.$emit('results-deleted');
        },

        afterAfterDeleteResults(cont) {
            cont();
            this.$root.$emit('cg::rubric-editor::reload');
        },

        openResult(result) {
            this.$emit('open-result', result);
        },
    },

    components: {
        Icon,
        Collapse,
        Loader,
        SubmitButton,
        AutoTestState,
    },
};
</script>

<style lang="less" scoped>
.results-table {
    margin-bottom: 0;

    th {
        border-top: 0;
    }

    .caret,
    .score,
    .state {
        width: 1px;
        white-space: nowrap;
    }

    .score {
        text-align: right;

        .fa-icon {
            transform: translateY(2px);
            margin-right: 0.5rem;
        }
    }

    .state {
        text-align: center;
    }
}
</style>

<style lang="less">
@import '~mixins.less';

.auto-test-run .pagination {
    display: flex;
    justify-content: center;

    .page-item .page-link {
        &:active,
        &:focus {
            box-shadow: none;
        }
        #app.dark & {
            border-color: @color-primary-darkest;
        }
    }

    #app.dark & .page-item .page-link {
        background-color: @color-primary;
        color: @text-color-dark;
    }

    .page-item.active .page-link {
        background-color: @color-primary;
        color: @text-color-dark;
        #app.dark & {
            background-color: @color-primary-darkest;
        }
    }
}
</style>
