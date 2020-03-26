/* SPDX-License-Identifier: AGPL-3.0-only */
<template>
<div class="analytics-dashboard row">
    <b-alert v-if="error"
             variant="danger"
             show>
        {{ $utils.getErrorMessage(error) }}
    </b-alert>

    <loader page-loader v-else-if="loading" />

    <div v-else-if="baseSubmissionData.submissionCount === 0"
         class="col-12">
        <h3 class="border rounded p-5 text-center text-muted font-italic">
            There are no submissions yet.
        </h3>
    </div>

    <template v-else>
        <div class="col-12">
            <b-card header="General statistics"
                    body-class="pb-0">
                <div class="row">
                    <div class="col-6 col-md-3 mb-3 border-right metric">
                        <h1>{{ baseSubmissionData.studentCount }}</h1>
                        <label>Students</label>

                        <description-popover triggers="hover"
                                             placement="top">
                            Submitted a total of
                            {{ baseSubmissionData.submissionCount }} submissions!
                        </description-popover>
                    </div>

                    <div class="col-6 col-md-3 mb-3 metric"
                         :class="{ 'border-right': $root.$isMediumWindow }">
                        <h1>{{ to2Dec(latestSubmissionData.averageGrade) }}</h1>
                        <label>Average grade</label>

                        <description-popover triggers="hover"
                                             placement="top">
                            The average grade over the latest submissions.
                        </description-popover>
                    </div>

                    <hr v-if="!$root.$isMediumWindow"
                        class="w-100 mt-0 mx-3"/>

                    <div class="col-6 col-md-3 mb-3 border-right metric">
                        <h1>{{ to2Dec(baseSubmissionData.averageSubmissions) }}</h1>
                        <label>Average number of submissions</label>

                        <description-popover triggers="hover"
                                             placement="top">
                            The average number of submissions per student.
                        </description-popover>
                    </div>

                    <div class="col-6 col-md-3 mb-3 metric">
                        <h1>{{ to2Dec(latestInlineFeedbackSource.averageEntries) }}</h1>
                        <label>Average number of feedback entries</label>

                        <description-popover triggers="hover"
                                             placement="top">
                            The average number of feedback entries over the latest submissions.
                        </description-popover>
                    </div>
                </div>
            </b-card>
        </div>

        <div class="col-12">
            <analytics-filters :assignment-id="assignmentId"
                               :workspace="baseWorkspace"
                               @results="filterResults = $event">
            </analytics-filters>
        </div>

        <loader page-loader :scale="4" v-if="filterResults.length === 0" />

        <div v-else-if="baseSubmissionData.submissionCount === 0"
            class="col-12">
            <h3 class="border rounded p-5 text-center text-muted font-italic">
                No submissions within the specified filter parameters.
            </h3>
        </div>

        <template v-else>
            <div class="col-12">
                <b-card header-class="d-flex pr-2">
                    <template #header>
                        <div class="flex-grow-1">
                            Students submitted on
                        </div>

                        <div class="d-flex flex-grow-0">
                            <div class="icon-button"
                                 :class="{ 'active': submissionDateRelative }"
                                 @click="submissionDateRelative = !submissionDateRelative"
                                 v-b-popover.top.hover="'Relative to filter group'">
                                <icon name="percent" />
                            </div>

                            <datetime-picker :value="submissionDateRange"
                                             @on-close="updateSubmissionDateRange"
                                             placeholder="Select dates"
                                             :config="{
                                                 mode: 'range',
                                                 defaultHour: undefined,
                                                 defaultMinute: undefined,
                                             }"
                                             class="ml-3 text-center"
                                             style="min-width: 20rem"/>

                            <b-input-group>
                                <input :value="submissionDateBinSize"
                                       @input="updateSubmissionDateBinSize"
                                       type="number"
                                       min="1"
                                       step="1"
                                       class="form-control ml-2 pt-1"
                                       style="max-width: 4rem;"/>

                                <b-form-select v-model="submissionDateBinUnit"
                                               :options="submissionDateBinUnits"
                                               class="pt-1"
                                               style="max-width: 5rem"/>
                            </b-input-group>
                        </div>
                    </template>

                    <bar-chart :chart-data="submissionDateHistogram"
                               :options="submissionDateOpts"
                               :width="300"
                               :height="75"/>
                </b-card>
            </div>

            <div class="col-12 col-lg-6"
                 :class="{ 'col-lg-12': largeGradeHistogram }">
                <b-card header="Grade statistics">
                    <loader center :scale="2" class="p-3" v-if="changingGradeHistSize" />

                    <bar-chart v-else
                               :chart-data="gradeHistogram"
                               :options="gradeHistOpts"
                               :width="300"
                               :height="largeGradeHistogram ? 133 : 200"/>
                </b-card>
            </div>

            <template v-if="rubricStatistic != null">
                <div class="col-12 col-lg-6"
                     :class="{ 'col-lg-12': largeGradeHistogram }">
                    <b-card header-class="d-flex pr-2">
                        <template #header>
                            <div class="flex-grow-1">
                                Rubric statistics
                            </div>

                            <div class="d-flex flex-grow-0">
                                <div v-if="rubricStatistic.hasRelative"
                                     class="icon-button"
                                     :class="{ 'active': rubricRelative }"
                                     @click="rubricRelative = !rubricRelative"
                                     v-b-popover.top.hover="'Relative to max score in category'">
                                    <icon name="percent" />
                                </div>

                                <b-form-select v-model="selectedRubricStatistic"
                                               :options="rubricStatOptions"
                                               class="ml-3 pt-1"
                                               style="max-width: 7.5rem"/>
                            </div>
                        </template>

                        <loader center :scale="2" class="p-3" v-if="changingGradeHistSize" />

                        <component v-else
                                   :is="rubricStatistic.chartComponent"
                                   :chart-data="rubricStatistic.data"
                                   :options="rubricStatistic.options"
                                   :width="300"
                                   :height="largeGradeHistogram ? 133 : 200"/>
                    </b-card>
                </div>
            </template>
        </template>
    </template>
</div>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';
import * as stat from 'simple-statistics';

import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/percent';

import { WorkspaceFilter } from '@/models';
import { BarChart, ScatterPlot } from '@/components/Charts';
import Loader from '@/components/Loader';
import DatetimePicker from '@/components/DatetimePicker';
import AnalyticsFilters from '@/components/AnalyticsFilters';
import DescriptionPopover from '@/components/DescriptionPopover';

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
            id: this.$utils.getUniqueId(),
            loading: true,
            error: null,

            baseWorkspace: null,
            filterResults: [],

            submissionDateRelative: true,
            submissionDateRange: [],
            submissionDateBinSize: 1,
            submissionDateBinUnit: 'days',

            rubricRelative: true,
            selectedRubricStatistic: null,

            // Changing `largeGradeHistogram` strangely does not trigger a
            // redraw of the charts that depend on it. So when it changes
            // we set this to `true` and then after a rerender back to `false`
            // again so the charts get properly resized.
            changingGradeHistSize: false,
        };
    },

    computed: {
        ...mapGetters('courses', ['assignments']),
        ...mapGetters('rubrics', { allRubricResults: 'results' }),

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

        baseSubmissionData() {
            return this.baseWorkspace.submissions;
        },

        latestSubmissions() {
            return this.baseWorkspace.filter([
                new WorkspaceFilter({ onlyLatestSubs: true }),
            ])[0];
        },

        latestSubmissionData() {
            return this.latestSubmissions.submissions;
        },

        latestInlineFeedbackSource() {
            return this.latestSubmissions.getSource('inline_feedback');
        },

        submissionSources() {
            return this.filterResults.map(r => r.submissions);
        },

        hasRubricSource() {
            return this.baseWorkspace && this.baseWorkspace.hasSource('rubric_data');
        },

        rubricSources() {
            if (!this.hasRubricSource) {
                return [];
            }
            return this.filterResults.map(r => r.getSource('rubric_data'));
        },

        hasManyRubricRows() {
            return this.$utils.getProps(this.rubricSource, 0, 'rowIds', 'length') > 8;
        },

        submissionsByDate() {
            return this.submissionSources.map(source =>
                source.binSubmissionsByDate(
                    this.submissionDateRange,
                    this.submissionDateBinSize,
                    this.submissionDateBinUnit,
                ),
            );
        },

        allSubmissionDates() {
            const dates = this.submissionsByDate.flatMap(Object.keys);
            return [...new Set(dates)].sort();
        },

        submissionDateBinUnits() {
            return [
                'minutes',
                'hours',
                'days',
                'weeks',
                'years',
            ];
        },

        submissionDateHistogram() {
            const allDates = this.allSubmissionDates;
            const datasets = this.submissionsByDate.map((bins, i) => {
                let data = allDates.map(d => bins[d].length);
                const nSubs = stat.sum(data);

                if (this.submissionDateRelative) {
                    data = data.map(x => 100 * x / nSubs);
                }

                return {
                    label: this.filterResults[i].filter.toString(),
                    data,
                };
            });

            return { labels: allDates, datasets };
        },

        submissionDateOpts() {
            const label = this.submissionDateRelative ? 'Percentage of students' : 'Number of students';
            return {
                scales: {
                    yAxes: [
                        {
                            ticks: {
                                beginAtZero: true,
                            },
                            scaleLabel: {
                                display: true,
                                labelString: label,
                            },
                        },
                    ],
                },
            };
        },

        largeGradeHistogram() {
            return this.$root.$isLargeWindow && (
                !this.hasRubricSource ||
                this.hasManyRubricRows ||
                this.filterResults.length > 2
            );
        },

        gradeHistogram() {
            let maxGrade = this.assignment.max_grade;
            if (maxGrade == null) {
                maxGrade = 10;
            }

            const bins = this.$utils.range(Math.ceil(maxGrade));
            const labels = bins.map(start => `${10 * start}% - ${10 * (start + 1)}%`);

            const datasets = this.submissionSources.map((source, i) => {
                const data = source.binSubmissionsByGrade();

                // We can't use source.submissionCount here, because some submissions
                // may have been filtered out, e.g. submissions without a grade.
                const nSubs = stat.sum(bins.map(bin => data[bin].length));

                return {
                    label: this.filterResults[i].filter.toString(),
                    data: bins.map(bin => 100 * data[bin].length / nSubs),
                };
            });

            return { labels, datasets };
        },

        gradeHistOpts() {
            return {
                scales: {
                    yAxes: [
                        {
                            ticks: {
                                beginAtZero: true,
                                stepSize: 5,
                            },
                            scaleLabel: {
                                display: true,
                                labelString: 'Percentage of students',
                            },
                        },
                    ],
                },
            };
        },

        rubricStatOptions() {
            const baseOpts = [
                { value: 'mean', text: 'Mean' },
                { value: 'median', text: 'Median' },
                { value: 'mode', text: 'Mode' },
                { value: 'rit', text: 'RIT' },
                { value: 'rir', text: 'RIR' },
            ];

            this.rubric.rows.forEach(row => {
                baseOpts.push({
                    text: `Correlation: ${row.header}`,
                    value: row.id,
                });
            });

            return baseOpts;
        },

        rubricStatistics() {
            const baseStats = {
                mean: {
                    chartComponent: 'bar-chart',
                    data: this.getRubricHistogramData('mean', this.rubricRelative),
                    options: this.rubricHistogramOpts,
                    hasRelative: true,
                },
                median: {
                    chartComponent: 'bar-chart',
                    data: this.getRubricHistogramData('median', this.rubricRelative),
                    options: this.rubricHistogramOpts,
                    hasRelative: true,
                },
                mode: {
                    chartComponent: 'bar-chart',
                    data: this.getRubricHistogramData('mode', this.rubricRelative),
                    options: this.rubricHistogramOpts,
                    hasRelative: true,
                },
                rit: {
                    chartComponent: 'bar-chart',
                    data: this.getRubricHistogramData('rit'),
                    options: this.rubricHistogramOpts,
                },
                rir: {
                    chartComponent: 'bar-chart',
                    data: this.getRubricHistogramData('rir'),
                    options: this.rubricHistogramOpts,
                },
            };

            this.rubric.rows.forEach(row => {
                baseStats[row.id] = {
                    chartComponent: 'scatter-plot',
                    data: this.getRubricScatterData(row),
                    options: this.rubricScatterOpts,
                };
            });

            return baseStats;
        },

        rubricStatistic() {
            if (this.selectedRubricStatistic == null) {
                return null;
            }
            return this.rubricStatistics[this.selectedRubricStatistic];
        },

        rubricNormalizeFactors() {
            if (!this.rubricRelative) {
                return null;
            }
            return this.rubric.rows.map(row => [row.minPoints, row.maxPoints]);
        },

        rubricHistogramOpts() {
            const getStats = (tooltipItem, data) => {
                const dataset = data.datasets[tooltipItem.datasetIndex];
                return dataset.stats[tooltipItem.index];
            };

            const labelCb = (tooltipItem, data) => {
                const stats = getStats(tooltipItem, data);
                return this.rirMessage(stats.rir);
            };

            const afterLabelCb = (tooltipItem, data) => {
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

            const label = this.rubricStatOptions.find(so =>
                so.value === this.selectedRubricStatistic,
            ).text;

            return {
                scales: {
                    yAxes: [
                        {
                            scaleLabel: {
                                display: true,
                                labelString: label,
                            },
                        },
                    ],
                },
                tooltips: {
                    callbacks: {
                        label: labelCb,
                        afterLabel: afterLabelCb,
                    },
                },
            };
        },

        rubricScatterOpts() {
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
                                labelString: 'Total score - Item score',
                            },
                        },
                    ],
                },
            };
        },
    },

    methods: {
        ...mapActions('analytics', ['loadWorkspace', 'clearAssignmentWorkspaces']),

        reset() {
            this.selectedRubricStatistic = 'mean';
            this.rubricRelative = true;
            this.filterResults = [];
        },

        loadWorkspaceData() {
            this.loading = true;
            this.baseWorkspace = null;
            return this.loadWorkspace({
                workspaceId: this.currentWorkspaceId,
            }).then(
                res => {
                    const ws = res.data;
                    if (ws.id === this.currentWorkspaceId) {
                        this.reset();
                        this.baseWorkspace = ws;
                        this.error = null;
                        this.loading = false;
                    }
                    return res;
                },
                err => {
                    this.loading = false;
                    this.error = err;
                    throw err;
                },
            );
        },

        reloadWorkspace() {
            this.clearAssignmentWorkspaces().then(this.loadWorkspaceData);
        },

        getRubricHistogramData(key, normalize) {
            const datasets = this.rubricSources.map((source, i) => {
                let data = [];
                const stats = [];

                this.rubric.rows.forEach(row => {
                    const rowStats = {
                        mean: source.meanPerCat[row.id],
                        mode: source.modePerCat[row.id],
                        median: source.medianPerCat[row.id],
                        rit: source.ritPerCat[row.id],
                        rir: source.rirPerCat[row.id],
                        nTimesFilled: source.nTimesFilledPerCat[row.id],
                        rowId: row.id,
                    };
                    stats.push(rowStats);
                    data.push(rowStats[key]);
                });

                if (normalize && this.rubricNormalizeFactors != null) {
                    data = this.normalize(data, this.rubricNormalizeFactors);
                }

                return {
                    label: this.filterResults[i].filter.toString(),
                    data,
                    stats,
                };
            });

            return {
                labels: this.rubric.rows.map(row => row.header),
                datasets,
            };
        },

        getRubricScatterData(row) {
            const datasets = this.rubricSources.map((source, i) => {
                const { ritItemsPerCat, rirItemsPerCat } = source;
                const ritItems = ritItemsPerCat[row.id];
                const rirItems = rirItemsPerCat[row.id];

                if (ritItems.length === 0 && rirItems.length === 0) {
                    return [];
                }

                return {
                    label: this.filterResults[i].filter.toString(),
                    data: rirItems.map(([x, y]) => ({ x, y })),
                };
            });

            return { datasets };
        },

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

        normalize(xs, factors) {
            if (typeof factors === 'number') {
                return xs.map(x => 100 * x / factors);
            } else if (Array.isArray(factors)) {
                return xs.map((x, i) => 100 * this.normalize1(x, factors[i]));
            } else {
                return xs;
            }
        },

        normalize1(x, [lower, upper]) {
            return x <= 0 ? -x / lower : x / upper;
        },

        updateSubmissionDateRange(event) {
            // Somehow this event is sometimes triggered without an array...
            if (typeof event === 'string') {
                return;
            }

            const curRange = this.submissionDateRange;
            if (
                event.length !== curRange.length ||
                !event.every((x, i) => console.log(x) || x.isSame(curRange[i]))
            ) {
                this.submissionDateRange = event;
            }
        },

        updateSubmissionDateBinSize(event) {
            const newSize = parseFloat(event.target.value);
            if (!Number.isNaN(newSize) && newSize !== this.submissionDateBinSize) {
                this.submissionDateBinSize = Number(newSize);
            }
        },
    },

    watch: {
        currentWorkspaceId: {
            immediate: true,
            handler() {
                this.loadWorkspaceData();
            },
        },

        async largeGradeHistogram() {
            // We must trigger a rerender when the box containing a chart's canvas
            // changes size.
            this.changingGradeHistSize = true;
            await this.$afterRerender();
            this.changingGradeHistSize = false;
        },
    },

    mounted() {
        this.$root.$on('cg::submissions-page::reload', this.reloadWorkspace);
    },

    destroyed() {
        this.$root.$off('cg::submissions-page::reload', this.reloadWorkspace);
    },

    components: {
        Icon,
        Loader,
        BarChart,
        ScatterPlot,
        AnalyticsFilters,
        DatetimePicker,
        DescriptionPopover,
    },
};
</script>

<style lang="less" scoped>
.metric {
    position: relative;
    text-align: center;

    label {
        padding: 0 1rem;
        margin-bottom: 0;
    }

    .description-popover {
        position: absolute;
        top: 0;
        right: 0.5rem;
    }
}
</style>

<style lang="less">
@import '~mixins.less';

.analytics-dashboard {
    .card {
        margin-bottom: 1rem;

        .input-group:not(:last-child) {
            margin-bottom: 1rem;
        }
    }

    .card-header {
        .custom-select,
        .form-control {
            height: 2rem;
            margin: -0.25rem 0;
            /* margin: -0.25rem -0.75rem; */
        }
    }

    // TODO: Define the .icon-button globally so we can use it
    // in other components as well.
    .icon-button {
        margin: -0.5rem -0.5rem -0.5rem 0.5rem;
        padding: 0.5rem;
        cursor: pointer;
        transition: background-color @transition-duration;

        &.active {
            color: lighten(@color-secondary, 5%);

            &.danger {
                color: @color-danger;
            }
        }

        &.text-muted {
            cursor: not-allowed;
        }

        &:not(.text-muted):hover {
            color: lighten(@color-secondary, 15%);

            &.danger {
                color: @color-danger;
            }
        }
    }
}
</style>
