/* SPDX-License-Identifier: AGPL-3.0-only */
<template>
<div class="analytics-dashboard row">
    <b-alert v-if="error"
             variant="danger"
             show>
        {{ $utils.getErrorMessage(error) }}
    </b-alert>

    <loader page-loader v-else-if="loading" />

    <div v-else-if="totalSubmissionCount === 0"
         class="col-12">
        <h3 class="border rounded p-5 text-center text-muted font-italic">
            There are no submissions yet.
        </h3>
    </div>

    <template v-else>
        <div class="col-12">
            <analytics-general-stats
                large
                :base-workspace="baseWorkspace"
                :grade-workspace="latestSubmissionsWorkspace"
                :feedback-workspace="latestSubmissionsWorkspace" />
        </div>

        <div class="col-12">
            <analytics-filters :assignment-id="assignmentId"
                               :workspace="baseWorkspace"
                               @results="filterResults = $event">
            </analytics-filters>
        </div>

        <loader page-loader :scale="4" v-if="filterResults.length === 0" />

        <div v-else-if="totalSubmissionCount === 0"
            class="col-12">
            <h3 class="border rounded p-5 text-center text-muted font-italic">
                No submissions within the specified filter parameters.
            </h3>
        </div>

        <template v-else>
            <div class="col-12">
                <b-card header-class="d-flex">
                    <template #header>
                        <div class="flex-grow-1">
                            Students submitted on
                        </div>

                        <div class="d-flex flex-grow-0">
                            <datetime-picker :value="submissionDateRange"
                                             @on-close="updateSubmissionDateRange"
                                             placeholder="Select dates"
                                             :config="{
                                                 mode: 'range',
                                                 enableTime: false,
                                                 defaultHour: undefined,
                                                 defaultMinute: undefined,
                                             }"
                                             class="ml-3 text-center"
                                             style="min-width: 20rem"/>

                            <b-input-group class="mb-0">
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
                                               style="max-width: 7.5rem"/>
                            </b-input-group>

                            <div class="icon-button"
                                 :class="{ 'active': submissionDateRelative }"
                                 @click="submissionDateRelative = !submissionDateRelative"
                                 v-b-popover.top.hover="'Relative to filter group'">
                                <icon name="percent" />
                            </div>

                            <div class="icon-button danger"
                                 @click="resetSubmissionDateParams"
                                 v-b-popover.top.hover="'Reset'">
                                <icon name="reply" />
                            </div>

                        </div>
                    </template>

                    <h3 v-if="submissionDateMessage"
                        class="p-3 text-center text-muted font-italic">
                        {{ submissionDateMessage }}
                    </h3>

                    <bar-chart v-else
                               :chart-data="submissionDateHistogram"
                               :options="submissionDateOpts"
                               :width="300"
                               :height="75"/>
                </b-card>
            </div>

            <div class="col-12 col-xl-6"
                 :class="{ 'col-xl-12': largeGradeHistogram }">
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
                <div class="col-12 col-xl-6"
                     :class="{ 'col-xl-12': largeGradeHistogram }">
                    <b-card header-class="d-flex">
                        <template #header>
                            <div class="flex-grow-1">
                                Rubric statistics
                            </div>

                            <div class="d-flex flex-grow-0">
                                <b-form-select v-model="selectedRubricStatistic"
                                               :options="rubricStatOptions"
                                               class="ml-3 pt-1"
                                               style="max-width: 7.5rem"/>

                                <div v-if="rubricStatistic.hasRelative"
                                     class="icon-button"
                                     :class="{ 'active': rubricRelative }"
                                     @click="rubricRelative = !rubricRelative"
                                     v-b-popover.top.hover="'Relative to max score in category'">
                                    <icon name="percent" />
                                </div>
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
import moment from 'moment';

import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/percent';

import { WorkspaceFilter } from '@/models/analytics';
import { BarChart, ScatterPlot } from '@/components/Charts';
import Loader from '@/components/Loader';
import DatetimePicker from '@/components/DatetimePicker';
import AnalyticsFilters from '@/components/AnalyticsFilters';
import AnalyticsGeneralStats from '@/components/AnalyticsGeneralStats';

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
            submissionDateBinSizeTimer: null,
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

        totalSubmissionCount() {
            return this.baseWorkspace.submissions.submissionCount;
        },

        latestSubmissionsWorkspace() {
            return this.baseWorkspace.filter([
                new WorkspaceFilter({ onlyLatestSubs: true }),
            ])[0];
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

        filterLabels() {
            return this.filterResults.map(f => f.filter.toString());
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

        submissionDateMessage() {
            if (this.submissionDateHistogram.labels.length === 0) {
                return 'No submission within this range!';
            } else if (this.submissionDateHistogram.labels.length > 500) {
                return 'Please select fewer bins.';
            }
            return null;
        },

        submissionDateHistogram() {
            const subs = this.submissionSources.map(source =>
                source.binSubmissionsByDate(
                    this.submissionDateRange,
                    this.submissionDateBinSize,
                    this.submissionDateBinUnit,
                ),
            );

            const format = this.submissionDateFormatter;
            const dateLookup = subs.reduce(
                (acc, bins) => {
                    Object.values(bins).forEach(bin => {
                        if (!acc[bin.start]) {
                            acc[bin.start] = format(bin.start, bin.end);
                        }
                    });
                    return acc;
                },
                {},
            );
            const allDates = Object.keys(dateLookup).sort();

            const datasets = subs.map((bins, i) => {
                let data = allDates.map(d =>
                    (bins[d] == null ? 0 : bins[d].data.length),
                );

                if (this.submissionDateRelative) {
                    const nSubs = stat.sum(data);
                    data = data.map(x => (nSubs > 0 ? 100 * x / nSubs : 0));
                }

                return {
                    label: this.filterLabels[i],
                    data,
                };
            });

            return {
                labels: allDates.map(k => dateLookup[k]),
                datasets,
            };
        },

        submissionDateFormatter() {
            const unit = this.submissionDateBinUnit;

            const format = (d, fmt) => moment(d).utc().format(fmt);

            switch (unit) {
                case 'minutes':
                    return start => format(start, 'ddd MM-DD HH:mm');
                case 'hours':
                    return start => format(start, 'ddd MM-DD HH:00');
                default:
                    return (start, end) => {
                        const fmt = 'ddd MM-DD';
                        // The times reported per bin are UTC UNIX epoch timestamps.
                        const s = format(start, fmt);
                        const e = format(end, fmt);
                        return s === e ? s : `${s} — ${e}`;
                    };
            }
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
            return (
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
                    label: this.filterLabels[i],
                    data: bins.map(bin => (nSubs ? 100 * data[bin].length / nSubs : 0)),
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
                cgScatter: {
                    withBestFit: true,
                },
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
            this.filterResults = [];
            this.resetRubricParams();
            this.resetSubmissionDateParams();
        },

        resetRubricParams() {
            this.selectedRubricStatistic = 'mean';
            this.rubricRelative = true;
        },

        resetSubmissionDateParams() {
            this.submissionDateRelative = true;
            this.submissionDateRange = [];
            this.submissionDateBinSize = 1;
            this.submissionDateBinUnit = 'days';
            clearTimeout(this.submissionDateBinSizeTimer);
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
                    // Make sure we render at least a minimal bar for each
                    // datapoint, otherwise we will not get a popover.
                    data.push(rowStats[key] == null ? 0 : rowStats[key]);
                });

                if (normalize && this.rubricNormalizeFactors != null) {
                    data = this.normalize(data, this.rubricNormalizeFactors);
                }

                return {
                    label: this.filterLabels[i],
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
                const { rirItemsPerCat } = source;
                const rirItems = rirItemsPerCat[row.id];

                return {
                    label: this.filterLabels[i],
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
            const newRange = event.map(d => moment(d));

            if (
                newRange.length !== curRange.length ||
                // Check if all the dates are the same as the previous to
                // prevent a rerender, e.g. in case a user just opened the
                // popover and immediately closes it by clicking somewhere
                // in the page.
                !newRange.every((x, i) => x.isSame(curRange[i]))
            ) {
                this.submissionDateRange = event;
            }
        },

        updateSubmissionDateBinSize(event) {
            clearTimeout(this.submissionDateBinSizeTimer);
            this.submissionDateBinSizeTimer = setTimeout(() => {
                const newSize = parseFloat(event.target.value);
                if (!Number.isNaN(newSize) && newSize !== this.submissionDateBinSize) {
                    this.submissionDateBinSize = Number(newSize);
                }
            }, 500);
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
        AnalyticsGeneralStats,
        DatetimePicker,
    },
};
</script>

<style lang="less" scoped>
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
            color: lighten(@color-secondary, 15%);

            &.danger {
                color: @color-danger;
            }
        }

        &.text-muted {
            cursor: not-allowed;
        }

        &:not(.text-muted):hover {
            color: lighten(@color-secondary, 5%);

            &.danger {
                color: darken(@color-danger, 10%);
            }
        }
    }
}
</style>
