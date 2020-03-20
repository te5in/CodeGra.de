/* SPDX-License-Identifier: AGPL-3.0-only */
<template>
<div class="analytics-dashboard row">
    <loader page-loader v-if="loading" />

    <template v-else>
        <div class="col-12">
            <b-card header="General statistics">
                <div class="row">
                    <div class="col-3 border-right metric">
                        <h1>{{ latestSubmissions.length }}</h1>
                        <label>Number of students</label>
                    </div>

                    <div class="col-3 border-right metric">
                        <h1>{{ to2Dec(workspace.averageGrade) }}</h1>
                        <label>Average grade</label>
                    </div>

                    <div class="col-3 border-right metric">
                        <h1>{{ to2Dec(workspace.averageSubmissions) }}</h1>
                        <label>Average number of submissions</label>
                    </div>

                    <div class="col-3 metric">
                        <h1>{{ to2Dec(inlineFeedbackSource.averageEntries) }}</h1>
                        <label>Average number of feedback entries</label>
                    </div>
                </div>
            </b-card>
        </div>

        <div class="col-12 col-lg-6"
            :class="{ 'col-lg-12': largeGradeHistogram }">
            <b-card header="Histogram of grades">
                <bar-chart :chart-data="gradeHistogram"
                           red-to-green
                           :width="300"
                           :height="largeGradeHistogram ? 100 : 200"/>
            </b-card>
        </div>

        <template v-if="hasRubric">
            <div class="col-12 col-lg-6"
                :class="{ 'col-lg-12': largeGradeHistogram }">
                <b-card header="Mean score per rubric category">
                    <bar-chart :chart-data="rubricMeanHistogram"
                               :width="300"
                               :height="largeGradeHistogram ? 100 : 200"/>
                </b-card>
            </div>

            <template v-for="row in rubric.rows"
                      v-if="rubricCatScatter[row.id]">
                <div class="col-12 col-lg-6">
                    <b-card :header="`${row.header}: Correlation of item score with total score`">
                        <scatter-plot :chart-data="rubricCatScatter[row.id]"
                                      :width="300"
                                      :height="200"/>
                    </b-card>
                </div>
            </template>
        </template>
    </template>
</div>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';

import { WorkspaceFilter } from '@/models';
import { BarChart, ScatterPlot } from '@/components/Charts';
import Loader from '@/components/Loader';

export default {
    name: 'analytics-dashboard',

    props: {
        assignmentId: {
            type: Number,
            required: true,
        },
    },

    data() {
        return {
            loading: true,
            currentWorkspace: null,
            currentRubricStat: 'mean',
        };
    },

    computed: {
        ...mapGetters('courses', ['assignments']),
        ...mapGetters('submissions', ['getLatestSubmissions']),
        ...mapGetters('rubrics', { allRubricResults: 'results' }),
        ...mapGetters('analytics', ['getWorkspace']),

        assignment() {
            return this.assignments[this.assignmentId];
        },

        workspaceIds() {
            return this.$utils.getProps(this.assignment, null, 'analytics_workspace_ids');
        },

        currentWorkspaceId() {
            return this.$utils.getProps(this.workspaceIds, null, 0);
        },

        rubric() {
            return this.$utils.getProps(this.assignment, null, 'rubric');
        },

        workspace() {
            return this.currentWorkspace.filter(this.filter);
        },

        rubricSource() {
            return this.workspace.getSource('rubric_data');
        },

        inlineFeedbackSource() {
            return this.workspace.getSource('inline_feedback');
        },

        hasRubric() {
            return this.rubricSource != null;
        },

        hasManyRubricRows() {
            return this.$utils.getProps(this.rubricSource, 0, 'rowIds', 'length');
        },

        latestSubmissions() {
            return this.getLatestSubmissions(this.assignmentId);
        },

        allSubmissionData() {
            return this.currentWorkspace.student_submissions;
        },

        filter() {
            return new WorkspaceFilter();
        },

        largeGradeHistogram() {
            return (
                this.$root.isLargeWindow &&
                (!this.hasRubric || this.hasManyRubricRows)
            );
        },

        gradeHistogram() {
            const bins = [...Array(10).keys()].map(x => [x, x + 1]);
            const labels = bins.map(([start, end]) => `${10 * start}% - ${10 * end}%`);
            const data = this.currentWorkspace.gradeHistogram(bins);

            const datasets = [
                {
                    label: 'Number of students',
                    data,
                },
            ];

            return {
                labels,
                datasets,
                options: this.gradeHistOpts,
            };
        },

        gradeHistOpts() {
            return {
                scales: {
                    yAxes: [
                        {
                            ticks: {
                                stepSize: 1,
                            },
                        },
                    ],
                },
            };
        },

        rubricMeanHistogram() {
            const source = this.rubricSource;

            if (source == null) {
                return null;
            }

            const data = [];
            const stats = [];

            this.rubric.rows.forEach(row => {
                const stat = {
                    rowId: row.id,
                    mean: source.meanPerCat[row.id],
                    mode: source.modePerCat[row.id],
                    median: source.medianPerCat[row.id],
                    rit: source.ritPerCat[row.id],
                    rir: source.rirPerCat[row.id],
                    nTimesFilled: source.nTimesFilledPerCat[row.id],
                };
                stats.push(stat);
                data.push(stat[this.currentRubricStat]);
            });

            return {
                labels: this.rubric.rows.map(row => row.header),
                datasets: [
                    {
                        label: 'Mean score',
                        data,
                        stats,
                    },
                ],
                options: this.rubricMeanHistOpts,
            };
        },

        rubricMeanHistOpts() {
            const getStats = (tooltipItem, data) => {
                const dataset = data.datasets[tooltipItem.datasetIndex];
                return dataset.stats[tooltipItem.index];
            };

            const label = (tooltipItem, data) => {
                const stats = getStats(tooltipItem, data);
                return this.rirMessage(stats.rir);
            };

            const afterLabel = (tooltipItem, data) => {
                const stats = getStats(tooltipItem, data);
                // Do not escape, chart.js does its own escaping.
                return [
                    `Times filled: ${stats.nTimesFilled}`,
                    `Mean: ${this.to2Dec(stats.mean)}`,
                    `Median: ${this.to2Dec(stats.median)}`,
                    `Mode: ${this.modeToString(stats.mode)}`,
                    `Rit: ${this.to2Dec(stats.rit) || '-'}`,
                    `Rir: ${this.to2Dec(stats.rir) || '-'}`,
                ];
            };

            return {
                tooltips: {
                    callbacks: {
                        label,
                        afterLabel,
                    },
                },
            };
        },

        rubricCatScatter() {
            const ritItems = this.rubricSource.ritItemsPerCat;
            const rirItems = this.rubricSource.rirItemsPerCat;

            return this.rubric.rows.reduce(
                (acc, row) => {
                    const ritItem = ritItems[row.id].map(([x, y]) => ({ x, y }));
                    const rirItem = rirItems[row.id].map(([x, y]) => ({ x, y }));

                    if (ritItem.length === 0 && rirItem.length === 0) {
                        return acc;
                    }

                    acc[row.id] = {
                        datasets: [
                            {
                                label: 'Total',
                                data: ritItem,
                            },
                            {
                                label: 'Total - Item',
                                data: rirItem,
                            },
                        ],
                        options: this.rubricScatterOpts,
                    };
                    return acc;
                },
                {},
            );
        },

        rubricCatScatterOpts() {
            return {
                scales: {
                    xAxes: [
                        {
                            scaleLabel: {
                                display: true,
                                labelString: 'Item score',
                            },
                        },
                    ],
                    yAxes: [
                        {
                            scaleLabel: {
                                display: true,
                                labelString: 'Total score (minus item score for rir)',
                            },
                        },
                    ],
                },
            };
        },
    },

    methods: {
        ...mapActions('analytics', ['loadWorkspace']),

        to2Dec(x) {
            return this.$utils.toMaxNDecimals(x, 2);
        },

        modeToString(mode) {
            // The mode is usually a number, but it can also be a list when multiple
            // values were the most common.
            if (Array.isArray(mode)) {
                return mode.map(this.to2Dec).join(', ');
            } else {
                return this.to2Dec(mode);
            }
        },

        rirMessage(rir) {
            if (rir == null) {
                return 'There was not enough data to calculate a meaningful Rir value.';
            } else if (rir < 0) {
                return 'The rir value is negative, which means ...';
            } else if (rir > 0.25) {
                return 'The rir value is very high, which means...';
            } else {
                return 'The rir value is very close to zero, which means...';
            }
        },
    },

    watch: {
        currentWorkspaceId: {
            immediate: true,
            async handler(newId) {
                this.loading = true;
                const ws = await this.loadWorkspace({ workspaceId: newId });
                if (ws.id === newId) {
                    this.currentWorkspace = this.getWorkspace(newId);
                    this.loading = false;
                }
            },
        },
    },

    components: {
        Loader,
        BarChart,
        ScatterPlot,
    },
};
</script>

<style lang="less" scoped>
.card {
    margin-bottom: 1rem;
}

.metric {
    text-align: center;

    label {
        padding: 0 1rem;
        margin-bottom: 0;
    }
}
</style>
