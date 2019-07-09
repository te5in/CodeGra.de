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
               :class="{ 'table-hover': run.results.length > 0 }">
            <thead>
                <tr>
                    <th class="name">Name</th>
                    <th class="score">Score</th>
                    <th class="state">State</th>
                </tr>
            </thead>

            <tbody v-if="run.results.length > 0">
                <tr v-for="result in run.results"
                    :key="submissions[result.submissionId].user.id"
                    @click="openResult(result)">
                    <td class="name">
                        {{ $utils.nameOfUser(submissions[result.submissionId].user) }}
                    </td>
                    <td class="score">
                        <icon v-if="submissions[result.submissionId].grade_overridden"
                                v-b-popover.top.hover="'This submission\'s calculated grade has been manually overridden'"
                                name="exclamation-triangle"/>
                        {{ $utils.toMaxNDecimals($utils.getProps(result, '-', 'pointsAchieved'), 2) }} /
                        {{ $utils.toMaxNDecimals(autoTest.pointsPossible, 2) }}
                    </td>
                    <td class="state">
                        <auto-test-state :result="result" />
                    </td>
                </tr>
            </tbody>
            <tbody v-else>
                <tr>
                    <td colspan="3">No results</td>
                </tr>
            </tbody>
        </table>
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

        submissions() {
            return this.assignment.submissions.reduce((acc, sub) => {
                acc[sub.id] = sub;
                return acc;
            }, {});
        },
    },

    methods: {
        ...mapActions('autotest', {
            storeDeleteAutoTestResults: 'deleteAutoTestResults',
        }),

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
        },

        openResult(result) {
            this.$emit('open-result', result);
        },
    },

    components: {
        Icon,
        Collapse,
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
