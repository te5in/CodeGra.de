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

            <div>
                <auto-test-state btn no-timer :result="run" />

                <submit-button
                    v-if="editable"
                    :submit="() => deleteResults(run.id)"
                    variant="danger"
                    confirm="Are you sure you want to delete the results?"
                    :label="run.finished ? 'Delete' : 'Stop'"/>
            </div>
        </b-card-header>

        <table slot="content"
               class="table table-striped results-table"
               :class="{ 'table-hover': run.results.length > 0 }">
            <thead>
                <tr>
                    <th class="name">Name</th>
                    <th class="score">Score</th>
                    <th class="state">State</th>
                </tr>
            </thead>

            <tbody>
                <template v-if="run.results.length > 0">
                    <tr v-for="result in run.results"
                        :key="`auto-test-result-${result.submission.user.id}`"
                        @click="openResult(result)">
                        <td class="name">{{ $utils.nameOfUser(result.submission.user) }}</td>
                        <td class="score">
                            <icon v-if="result.submission.grade_overridden"
                                    v-b-popover.top.hover="'This submission\'s calculated grade has been manually overridden'"
                                    name="exclamation-triangle"/>
                            {{ $utils.toMaxNDecimals($utils.getProps(result, '-', 'pointsAchieved'), 2) }} /
                            {{ $utils.toMaxNDecimals(autoTest.pointsPossible, 2) }}
                        </td>
                        <td class="state">
                            <auto-test-state :result="result" />
                        </td>
                    </tr>
                </template>
                <template v-else>
                    <tr>
                        <td colspan="3">No results</td>
                    </tr>
                </template>
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

    methods: {
        ...mapActions('autotest', {
            storeDeleteAutoTestResults: 'deleteAutoTestResults',
        }),

        deleteResults(id) {
            return this.storeDeleteAutoTestResults({
                autoTestId: this.autoTest.id,
                runId: id,
            });
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
