/* SPDX-License-Identifier: AGPL-3.0-only */
<template>
<div class="analytics-dashboard row">
    <div v-if="error"
         class="col-12">
        <b-alert show
                 variant="danger"
                 class="col-12">
            {{ $utils.getErrorMessage(error) }}
        </b-alert>
    </div>

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

        <div class="col-12 mt-3">
            <analytics-filters :assignment-id="assignmentId"
                               :workspace="baseWorkspace"
                               :initial-data="filters"
                               @serialize="filters = $event"
                               @results="filterResults = $event">
            </analytics-filters>
        </div>

        <loader page-loader :scale="4" v-if="filterResults.length === 0" />

        <div v-else-if="filteredSubmissionCount === 0"
             class="col-12 mt-3">
            <h3 class="border rounded p-5 text-center text-muted font-italic">
                No submissions within the specified filter parameters.
            </h3>
        </div>

        <template v-else>
            <div class="col-12 mt-3">
                <b-card header-class="d-flex"
                        :body-class="noSubmissionWithinSelectedDates ? 'center' : ''">
                    <template #header>
                        <div class="flex-grow-1">
                            Students submitted on
                        </div>

                        <div class="d-flex flex-grow-0">
                            <b-button :variant="submissionDateRelative ? 'primary' : 'outline-primary'"
                                      @click="submissionDateRelative = !submissionDateRelative"
                                      v-b-popover.top.hover="'Relative to filter group'"
                                      class="ml-3">
                                <icon name="percent" />
                            </b-button>

                            <datetime-picker :value="submissionDateRange"
                                             @on-close="updateSubmissionDateRange"
                                             placeholder="Select dates"
                                             :config="{
                                                 mode: 'range',
                                                 enableTime: false,
                                                 minDate: minSubmissionDate,
                                                 maxDate: maxSubmissionDate,
                                             }"
                                             class="ml-2 text-center"/>

                            <b-input-group class="mb-0">
                                <input :value="submissionDateBinSize"
                                       @input="updateSubmissionDateBinSize"
                                       type="number"
                                       min="1"
                                       step="1"
                                       class="form-control ml-2 pt-1"
                                       style="max-width: 4rem;"/>

                                <b-form-select :value="submissionDateBinUnit"
                                               @input="updateSubmissionDateBinUnit"
                                               :options="submissionDateBinUnits"
                                               class="pt-1"
                                               style="max-width: 7.5rem"/>
                            </b-input-group>

                            <div class="icon-button danger"
                                 @click="resetSubmissionDateParams"
                                 v-b-popover.top.hover="'Reset'">
                                <icon name="reply" />
                            </div>

                            <description-popover class="icon-button ml-1"
                                                 placement="bottom"
                                                 :scale="1">
                                <p class="mb-2">
                                    This histogram shows at what times
                                    students have submitted their work.
                                    You can change the range of dates
                                    that is displayed and the bin size
                                    of the histogram.
                                </p>

                                <p>
                                    By default this shows the percentage of
                                    students in the respective filter group
                                    that have submitted in some interval.
                                    You can see the total number of students
                                    by clicking the
                                    <icon name="percent" :scale="0.75" class="mx-1" />
                                    button.
                                </p>
                            </description-popover>
                        </div>
                    </template>

                    <template v-if="noSubmissionWithinSelectedDates">
                        <h3 class="p-3 text-muted font-italic">
                            No submissions within this range!
                        </h3>
                    </template>

                    <template v-else-if="tooMuchSubmissionDateBins && !forceRenderSubmissionDates">
                        <p class="p-3 text-muted font-italic">
                            The selected range contains a lot of data points and
                            rendering the graph may freeze your browser.
                            Please select fewer bins or click the button below to
                            render the dataset anyway.
                        </p>

                        <b-button variant="primary"
                                  class="float-right"
                                  @click="forceRenderSubmissionDates = true">
                            Render anyway
                        </b-button>
                    </template>

                    <bar-chart v-else
                               :chart-data="submissionDateHistogram"
                               :options="submissionDateOpts"
                               :width="300"
                               :height="$root.$isXLargeWindow ? 75 : 100"/>
                </b-card>
            </div>

            <div class="col-12 mt-3">
                <b-card header-class="d-flex">
                    <template #header>
                        <div class="flex-grow-1">
                            Grade statistics
                        </div>

                        <div class="d-flex flex-grow-0">
                            <b-button :variant="gradeHistRelative ? 'primary' : 'outline-primary'"
                                      @click="gradeHistRelative = !gradeHistRelative"
                                      v-b-popover.top.hover="'Relative to filter group'"
                                      class="ml-3">
                                <icon name="percent" />
                            </b-button>

                            <b-input-group class="mb-0">
                                <input v-model="gradeHistBinSize"
                                       type="number"
                                       min="1"
                                       step="1"
                                       class="form-control ml-2 pt-1"
                                       style="max-width: 4rem;"/>
                            </b-input-group>

                            <description-popover class="icon-button ml-1"
                                                 placement="bottom"
                                                 :scale="1">
                                <p class="mb-2">
                                    The grade histogram shows the amount of
                                    students that got a certain grade for
                                    this assignment. You can change the bin
                                    size; fractional numbers are supported.
                                </p>

                                <p>
                                    By default this shows the percentage of
                                    students in the respective filter group
                                    that have submitted in some interval.
                                    You can see the total number of students
                                    by clicking the
                                    <icon name="percent" :scale="0.75" class="mx-1" />
                                    button.
                                </p>
                            </description-popover>
                        </div>
                    </template>

                    <bar-chart :chart-data="gradeHistogram"
                               :options="gradeHistOpts"
                               :width="300"
                               :height="100"/>
                </b-card>
            </div>

            <template v-if="rubricStatistic != null">
                <div class="col-12 mt-3">
                    <b-card header-class="d-flex"
                            :body-class="rubricChartEmpty ? 'center' : ''">
                        <template #header>
                            <div class="flex-grow-1">
                                Rubric statistics
                            </div>

                            <div class="d-flex flex-grow-0">
                                <b-button v-if="rubricStatistic.hasRelative"
                                          :variant="rubricRelative ? 'primary' : 'outline-primary'"
                                          @click="rubricRelative = !rubricRelative"
                                          v-b-popover.top.hover="'Relative to max score in category'">
                                    <icon name="percent" />
                                </b-button>

                                <b-form-select v-model="rubricSelectedStatistic"
                                               :options="rubricStatOptions"
                                               class="ml-2"
                                               style="max-width: 7.5rem"/>

                                <description-popover class="icon-button ml-1"
                                                     placement="bottom"
                                                     :scale="1">
                                    <p v-if="rubricSelectedStatistic === 'mean'"
                                       class="mb-2">
                                        The mean histogram displays the mean
                                        achieved score per rubric category.
                                        The error bars indicate the standard
                                        deviation of the sample of students.
                                    </p>

                                    <p v-else-if="rubricSelectedStatistic === 'median'"
                                       class="mb-2">
                                        The median histogram displays the median
                                        of the achieved scores per rubric
                                        category. The median is obtained by
                                        picking the middle value of a sorted
                                        sample.
                                    </p>

                                    <p v-else-if="rubricSelectedStatistic === 'mode'"
                                       class="mb-2">
                                        The mode histogram displays the mode of
                                        the achieved scores per rubric
                                        category. The mode is the most common
                                        value in a sample.
                                    </p>

                                    <template v-else-if="rubricSelectedStatistic === 'rit'">
                                        <p class="mb-2">
                                            The RIT value of a rubric category
                                            is Pearson's correlation
                                            coefficient between the achieved
                                            scores in that category and the
                                            total scores achieved for the
                                            entire rubric.
                                        </p>

                                        <p>
                                            The RIT value measures whether
                                            students who scored high in
                                            a rubric category also scored high
                                            on the rubric overall.
                                        </p>
                                    </template>

                                    <template v-else-if="rubricSelectedStatistic === 'rir'">
                                        <p class="mb-2">
                                            The RIR value of a rubric category
                                            is Pearson's correlation
                                            coefficient between the achieved
                                            scores in that category and the
                                            total scores achieved for the
                                            entire rubric minus the achieved
                                            score for the category.
                                        </p>

                                        <p class="mb-2">
                                            The RIR value measures whether
                                            students who scored high in
                                            a rubric category also scored high
                                            on the rubric overall.
                                        </p>

                                        <p>
                                            While the RIR value is very similar
                                            to the RIT value, it is a fairer
                                            representation of the explanatory
                                            factor of a rubric category because
                                            if the achieved points in the
                                            current category weren't removed,
                                            higher scores in the current
                                            category would contribute to higher
                                            overall scores in the rubric.
                                        </p>
                                    </template>

                                    <template v-else>
                                        <p class="mb-2">
                                            This plot shows a dot for each
                                            student that shows how much points
                                            someone achieved in the category
                                            "{{ rubric.rowsById[rubricSelectedStatistic].header }}"
                                            versus the total achieved points
                                            for the entire rubric minus the
                                            points scored in this category.
                                        </p>

                                        <p class="mb-2">
                                            The line is a linear regression of
                                            the data points and may provide more
                                            insight in the RIR value for this rubric category.
                                            An increasing line
                                            indicates that students who scored
                                            higher in this category also scored
                                            higher in the rest of the rubric,
                                            while a decreasing line indicates the
                                            opposite. If the line is decreasing,
                                            this rubric category may need a review!
                                        </p>
                                    </template>

                                    <p v-if="rubricStatistic.hasRelative">
                                        By default this shows the percentage of
                                        students in the respective filter group
                                        that have submitted in some interval.
                                        You can see the total number of students
                                        by clicking the
                                        <icon name="percent" :scale="0.75" class="mx-1" />
                                        button.
                                    </p>
                                </description-popover>
                            </div>
                        </template>

                        <template v-if="rubricChartEmpty">
                            <h3 class="p-4 text-muted font-italic">
                                No data for this statistic!
                            </h3>
                        </template>

                        <component v-else
                                   :is="rubricStatistic.chartComponent"
                                   :chart-data="rubricStatistic.data"
                                   :options="rubricStatistic.options"
                                   :width="300"
                                   :height="100"/>
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
import errorBarsPlugin from 'chartjs-plugin-error-bars';

import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/percent';

import { WorkspaceFilter } from '@/models/analytics';
import { BarChart, ScatterPlot } from '@/components/Charts';
import Loader from '@/components/Loader';
import DatetimePicker from '@/components/DatetimePicker';
import AnalyticsFilters from '@/components/AnalyticsFilters';
import DescriptionPopover from '@/components/DescriptionPopover';
import AnalyticsGeneralStats from '@/components/AnalyticsGeneralStats';
import { deepEquals, filterObject } from '@/utils';

export default {
    name: 'analytics-dashboard',

    props: {
        assignmentId: {
            type: Number,
            required: true,
        },
    },

    data() {
        const { analytics } = this.$route.query;
        const settings = analytics == null ? {} : JSON.parse(analytics);

        return {
            id: this.$utils.getUniqueId(),
            loading: true,
            error: null,

            baseWorkspace: null,

            ...this.fillSettings(settings),

            // Changing the submission date bin size can cause a lot of
            // bins to be drawn, especially when typing something like
            // `10`, where the value is temporarily `1`. We debounce the
            // event of the bin size input with this timer to prevent
            // temporary page freezes or flickering of the "too many bins"
            // message when editing the bin size.
            submissionDateBinSizeTimer: null,

            // When there are a lot of datapoints to draw in a chart the
            // browser may freeze, so we put a soft cap at 100. Users can
            // still choose to render the chart anyway, in which case this
            // boolean is temporarily set to true.
            forceRenderSubmissionDates: false,
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

        filteredSubmissionCount() {
            return this.filterResults.reduce(
                (acc, result) => {
                    result.submissions.submissionIds.forEach(id => acc.add(id));
                    return acc;
                },
                new Set(),
            ).size;
        },

        latestSubmissionsWorkspace() {
            return this.baseWorkspace.filter([new WorkspaceFilter({ onlyLatestSubs: true })])[0];
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

        filterLabels() {
            return this.filterResults.map(f => f.filter.toString());
        },

        minSubmissionDate() {
            const firstPerSource = this.submissionSources.map(source => source.firstSubmissionDate);
            const first = firstPerSource.reduce(
                (f, d) => (f == null || f.isAfter(d) ? d : f),
                null,
            );
            return first.toISOString();
        },

        maxSubmissionDate() {
            const lastPerSource = this.submissionSources.map(source => source.lastSubmissionDate);
            const last = lastPerSource.reduce((l, d) => (l == null || l.isBefore(d) ? d : l), null);
            return last.toISOString();
        },

        submissionDateBinUnits() {
            return ['minutes', 'hours', 'days', 'weeks', 'years'];
        },

        noSubmissionWithinSelectedDates() {
            const datasets = this.submissionDateHistogram.datasets;
            return stat.sum(datasets.flatMap(ds => ds.data)) === 0;
        },

        tooMuchSubmissionDateBins() {
            return this.submissionDateHistogram.labels.length > 100;
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
            const dateLookup = subs.reduce((acc, bins) => {
                Object.values(bins).forEach(bin => {
                    if (!acc[bin.start]) {
                        acc[bin.start] = format(bin.start, bin.end);
                    }
                });
                return acc;
            }, {});
            const allDates = Object.keys(dateLookup).sort();

            const datasets = subs.map((bins, i) => {
                const absData = allDates.map(d => (bins[d] == null ? 0 : bins[d].data.length));
                const nSubs = stat.sum(absData);
                const relData = absData.map(x => (nSubs > 0 ? 100 * x / nSubs : 0));

                return {
                    label: this.filterLabels[i],
                    absData,
                    relData,
                    data: this.submissionDateRelative ? relData : absData,
                };
            });

            return {
                labels: allDates.map(k => dateLookup[k]),
                datasets,
            };
        },

        submissionDateFormatter() {
            const unit = this.submissionDateBinUnit;

            const format = (d, fmt) =>
                moment(d)
                    .utc()
                    .format(fmt);

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
            const getDataset = (tooltipItem, data) =>
                data.datasets[tooltipItem.datasetIndex];

            const label = (tooltipItem, data) => {
                const ds = getDataset(tooltipItem, data);
                return ds.label;
            };

            const afterLabel = (tooltipItem, data) => {
                const ds = getDataset(tooltipItem, data);
                const abs = ds.absData[tooltipItem.index];
                const rel = ds.relData[tooltipItem.index];

                // Do not escape, chart.js does its own escaping.
                return [
                    `Number of students: ${abs}`,
                    `Percentage of students: ${this.to2Dec(rel)}`,
                ];
            };

            const labelString = this.submissionDateRelative
                ? 'Percentage of students'
                : 'Number of students';

            return {
                scales: {
                    yAxes: [
                        {
                            ticks: {
                                beginAtZero: true,
                            },
                            scaleLabel: {
                                display: true,
                                labelString,
                            },
                        },
                    ],
                },
                tooltips: {
                    callbacks: { label, afterLabel },
                },
            };
        },

        gradeHistogram() {
            let maxGrade = this.assignment.max_grade;
            if (maxGrade == null) {
                maxGrade = 10;
            }

            let binSize = parseFloat(this.gradeHistBinSize);
            if (Number.isNaN(binSize)) {
                binSize = 1;
            }

            window.range = this.$utils.range;

            const bins = this.$utils.range(0, Math.ceil(maxGrade / binSize));
            const labels = bins.map(i => {
                const start = this.to2Dec(i * binSize);
                const end = this.to2Dec(Math.min(maxGrade, (i + 1) * binSize));
                return `${start} - ${end}`;
            });

            const datasets = this.submissionSources.map((source, i) => {
                const data = source.binSubmissionsByGrade(binSize);

                const absData = bins.map(bin => data[bin].length);
                // We can't use source.submissionCount here, because some submissions
                // may have been filtered out, e.g. submissions without a grade.
                const nSubs = stat.sum(bins.map(bin => data[bin].length));
                const relData = absData.map(d => (nSubs ? (100 * d) / nSubs : 0));

                return {
                    label: this.filterLabels[i],
                    absData,
                    relData,
                    data: this.gradeHistRelative ? relData : absData,
                };
            });

            return { labels, datasets };
        },

        gradeHistOpts() {
            const getDataset = (tooltipItem, data) =>
                data.datasets[tooltipItem.datasetIndex];

            const label = (tooltipItem, data) => {
                const ds = getDataset(tooltipItem, data);
                return ds.label;
            };

            const afterLabel = (tooltipItem, data) => {
                const ds = getDataset(tooltipItem, data);
                const abs = ds.absData[tooltipItem.index];
                const rel = ds.relData[tooltipItem.index];

                // Do not escape, chart.js does its own escaping.
                return [
                    `Number of students: ${abs}`,
                    `Percentage of students: ${this.to2Dec(rel)}`,
                ];
            };

            const labelString = this.gradeHistRelative
                ? 'Percentage of students'
                : 'Number of students';

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
                                labelString,
                            },
                        },
                    ],
                },
                tooltips: {
                    callbacks: { label, afterLabel },
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
            if (this.rubricSelectedStatistic == null) {
                return null;
            }
            return this.rubricStatistics[this.rubricSelectedStatistic];
        },

        rubricChartEmpty() {
            if (this.rubricStatistic == null) {
                return true;
            } else {
                return this.rubricStatistic.data.datasets.every(ds => ds.data.length === 0);
            }
        },

        rubricNormalizeFactors() {
            if (!this.rubricRelative) {
                return null;
            }
            return this.rubric.rows.map(row => [row.minPoints, row.maxPoints]);
        },

        rubricHistogramOpts() {
            const getDataset = (tooltipItem, data) =>
                data.datasets[tooltipItem.datasetIndex];

            const label = (tooltipItem, data) => {
                const ds = getDataset(tooltipItem, data);
                return ds.label;
            };

            const afterLabel = (tooltipItem, data) => {
                const ds = getDataset(tooltipItem, data);
                const stats = ds.stats[tooltipItem.index];

                // Do not escape, chart.js does its own escaping.
                return [
                    `Times filled: ${stats.nTimesFilled}`,
                    `Mean: ${this.to2Dec(stats.mean)}`,
                    `Std. deviation: ${this.to2Dec(stats.stdev)}`,
                    `Median: ${this.to2Dec(stats.median)}`,
                    `Mode: ${this.modeToString(stats.mode)}`,
                    `Rit: ${this.to2Dec(stats.rit) || '-'}`,
                    `Rir: ${this.to2Dec(stats.rir) || '-'}`,
                    this.rirMessage(stats.rir),
                ];
            };

            const labelString = this.rubricStatOptions.find(
                so => so.value === this.rubricSelectedStatistic,
            ).text;

            return {
                scales: {
                    yAxes: [
                        {
                            scaleLabel: {
                                display: true,
                                labelString,
                            },
                        },
                    ],
                },
                tooltips: {
                    callbacks: { label, afterLabel },
                },
                plugins: [errorBarsPlugin],
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

        serializedData() {
            const defaults = this.fillSettings();
            const serialized = {
                filters: this.$utils.getProps(this, [], 'filters'),
                submissionDateRelative: this.submissionDateRelative,
                submissionDateRange: this.submissionDateRange,
                submissionDateBinSize: this.submissionDateBinSize,
                submissionDateBinUnit: this.submissionDateBinUnit,
                gradeHistRelative: this.gradeHistRelative,
                gradeHistBinSize: this.gradeHistBinSize,
                rubricRelative: this.rubricRelative,
                rubricSelectedStatistic: this.rubricSelectedStatistic,
            };

            return JSON.stringify(filterObject(serialized, (val, key) =>
                !deepEquals(val, defaults[key]),
            ));
        },
    },

    methods: {
        ...mapActions('analytics', ['loadWorkspace', 'clearAssignmentWorkspaces']),

        fillSettings(settings) {
            const filters = this.$utils.getProps(settings, [{}], 'filters');
            return Object.assign(
                {
                    filters,
                    filterResults: [],
                },
                this.fillRubricSettings(settings),
                this.fillGradeHistSettings(settings),
                this.fillSubmissionDateSettings(settings),
            );
        },

        fillRubricSettings(settings) {
            return Object.assign({
                rubricRelative: true,
                rubricSelectedStatistic: 'mean',
            }, settings);
        },

        fillGradeHistSettings(settings) {
            return Object.assign({
                gradeHistRelative: true,
                gradeHistBinSize: 1,
            }, settings);
        },

        fillSubmissionDateSettings(settings) {
            return Object.assign({
                submissionDateRelative: true,
                submissionDateRange: [],
                submissionDateBinSize: 1,
                submissionDateBinUnit: 'days',
            }, settings);
        },

        reset() {
            Object.assign(this, this.fillSettings());
        },

        resetRubricParams() {
            Object.assign(this, this.fillRubricSettings());
        },

        resetSubmissionDateParams() {
            Object.assign(this, this.fillSubmissionDateSettings());

            this.forceRenderSubmissionDates = false;
            clearTimeout(this.submissionDateBinSizeTimer);
        },

        resetGradeHistParams() {
            Object.assign(this, this.fillGradeHistSettings());
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
            const labels = this.rubric.rows.map(row => row.header);

            const datasets = this.rubricSources.map((source, i) => {
                const data = [];
                const stats = [];

                this.rubric.rows.forEach(row => {
                    const rowStats = {
                        mean: source.meanPerCat[row.id],
                        stdev: source.stdevPerCat[row.id],
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

                let errorBars = null;
                if (key === 'mean') {
                    errorBars = stats.map(st => st.stdev);
                }

                let normalized = data;
                if (normalize && this.rubricNormalizeFactors != null) {
                    normalized = this.normalize(data, this.rubricNormalizeFactors);

                    if (errorBars != null) {
                        errorBars = stats.map(({ stdev }, j) => (normalized[j] / data[j]) * stdev);
                    }
                }

                return {
                    label: this.filterLabels[i],
                    data: normalized,
                    stats,
                    errorBars: errorBars == null ? null : errorBars.reduce((acc, stdev, j) => {
                        acc[labels[j]] = { plus: stdev, minus: -stdev };
                        return acc;
                    }, {}),
                };
            });

            return {
                labels,
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
            const curRange = this.submissionDateRange;
            const newRange = event.map(d => moment(d));

            if (
                newRange.length !== curRange.length ||
                // Check if all the dates are the same as the previous to
                // prevent a rerender, e.g. in case a user just opened the
                // popover and immediately closes it by clicking somewhere
                // in the page.
                !newRange.every((d, i) => d.isSame(curRange[i]))
            ) {
                this.forceRenderSubmissionDates = false;
                this.submissionDateRange = event;
            }
        },

        updateSubmissionDateBinSize(event) {
            clearTimeout(this.submissionDateBinSizeTimer);
            this.submissionDateBinSizeTimer = setTimeout(() => {
                const newSize = parseFloat(event.target.value);
                if (!Number.isNaN(newSize) && newSize !== this.submissionDateBinSize) {
                    this.submissionDateBinSize = Number(newSize);
                    this.forceRenderSubmissionDates = false;
                }
            }, 500);
        },

        updateSubmissionDateBinUnit(event) {
            this.forceRenderSubmissionDates = false;
            this.submissionDateBinUnit = event;
        },
    },

    watch: {
        currentWorkspaceId: {
            immediate: true,
            handler(newVal, oldVal) {
                this.loadWorkspaceData().then(() => {
                    // Reset all configuration only when we are changing
                    // to another workspace, but not when loading the
                    // component for the first time.
                    if (newVal !== oldVal && oldVal != null) {
                        this.reset();
                    }
                });
            },
        },

        serializedData() {
            this.$router.replace({
                query: {
                    ...this.$route.query,
                    analytics: this.serializedData,
                },
                hash: this.$route.hash,
            });
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
        DescriptionPopover,
        AnalyticsGeneralStats,
        DatetimePicker,
    },
};
</script>

<style lang="less">
@import '~mixins.less';

.analytics-dashboard {
    .col-12 {
        display: flex;
        flex-direction: column;
    }

    .card {
        flex: 1 1 auto;

        .input-group:not(:last-child) {
            margin-bottom: 1rem;
        }
    }

    .card-header {
        .btn,
        .custom-select,
        .form-control {
            height: 2rem;
            margin: -0.25rem 0;
            padding-top: 0.25rem;
        }

        .btn {
            padding: 0.25rem 0.5rem;
            box-shadow: none !important;
        }
    }

    .card-body.center {
        display: flex;
        justify-content: center;
        align-items: center;
    }

    // TODO: Define the .icon-button globally so we can use it
    // in other components as well.
    .icon-button {
        margin: -0.5rem -0.5rem -0.5rem 0.5rem;
        padding: 0.5rem;
        cursor: pointer;
        transition: background-color @transition-duration;

        &:focus,
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
