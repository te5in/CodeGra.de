<template>
<b-card class="analytics-rubric-stats"
        header-class="d-flex"
        :body-class="chartEmpty ? 'center' : ''">
    <template #header>
        <div class="flex-grow-1">
            Rubric statistics
        </div>

        <div class="d-flex flex-grow-0">
            <b-button v-if="selectedStatistic.hasRelative"
                      :variant="relative ? 'primary' : 'outline-primary'"
                      @click="relative = !relative"
                      v-b-popover.top.hover="'Relative to max score in category'">
                <icon name="percent" />
            </b-button>

            <b-form-select v-model="metric"
                           :options="metricOptions"
                           class="ml-2"
                           style="max-width: 7.5rem"/>

            <description-popover class="icon-button ml-1"
                                 placement="bottom"
                                 :scale="1">
                <p v-if="metric === 'mean'"
                   class="mb-2">
                    The mean histogram displays the mean achieved score per
                    rubric category.  The error bars indicate the standard
                    deviation of the sample of students.
                </p>

                <p v-else-if="metric === 'median'"
                   class="mb-2">
                    The median histogram displays the median of the achieved
                    scores per rubric category. The median is obtained by
                    picking the middle value of a sorted sample.
                </p>

                <p v-else-if="metric === 'mode'"
                   class="mb-2">
                    The mode histogram displays the mode of the achieved scores
                    per rubric category. The mode is the most common value in
                    a sample.
                </p>

                <template v-else-if="metric === 'rit'">
                    <p class="mb-2">
                        The RIT value of a rubric category is Pearson's
                        correlation coefficient between the achieved scores in
                        that category and the total scores achieved for the
                        entire rubric.
                    </p>

                    <p>
                        The RIT value measures whether students who scored high
                        in a rubric category also scored high on the rubric
                        overall.
                    </p>
                </template>

                <template v-else-if="metric === 'rir'">
                    <p class="mb-2">
                        The RIR value of a rubric category is Pearson's
                        correlation coefficient between the achieved scores in
                        that category and the total scores achieved for the
                        entire rubric minus the achieved score for the
                        category.
                    </p>

                    <p class="mb-2">
                        The RIR value measures whether students who scored high
                        in a rubric category also scored high on the rubric
                        overall. The value is a number between -1 and 1. Higher
                        values are more desirable.
                    </p>

                    <p class="mb-2">
                        A RIR value greater than 0.25 means there is a strong
                        correlation between student scores in this rubric
                        category and their overall scores for the rubric.
                    </p>

                    <p class="mb-2">
                        A negative RIR value is a sign that something may be
                        off with a rubric category, as it means that students
                        who scored higher in a rubric category scored lower in
                        the overall rubric.
                    </p>

                    <p class="mb-2">
                        While the RIR value is very similar to the RIT value,
                        it is a fairer representation of the explanatory factor
                        of a rubric category because if the achieved points in
                        the current category weren't removed, higher scores in
                        the current category would contribute to higher overall
                        scores in the rubric.
                    </p>
                </template>

                <template v-else>
                    <p class="mb-2">
                        This plot shows a dot for each student that shows how
                        much points someone achieved in the category
                        "{{ rubric.rowsById[metric].header }}" versus the total
                        achieved points for the entire rubric minus the points
                        scored in this category.
                    </p>

                    <p class="mb-2">
                        The line is a linear regression of the data points and
                        may provide more insight in the RIR value for this
                        rubric category.  An increasing line indicates that
                        students who scored higher in this category also scored
                        higher in the rest of the rubric, while a decreasing
                        line indicates the opposite. If the line is decreasing,
                        this rubric category may need a review!
                    </p>
                </template>

                <p v-if="selectedStatistic.hasRelative">
                    By default this shows the percentage of students in the
                    respective filter group that have submitted in some
                    interval.  You can see the total number of students by
                    clicking the
                    <icon name="percent" :scale="0.75" class="mx-1" />
                    button.
                </p>
            </description-popover>
        </div>
    </template>

    <template v-if="chartEmpty">
        <h3 class="p-4 text-muted font-italic">
            No data for this statistic!
        </h3>
    </template>

    <component v-else
               :is="selectedStatistic.chartComponent"
               :chart-data="selectedStatistic.data"
               :options="selectedStatistic.options"
               :width="300"
               :height="100"/>
</b-card>
</template>

<script>
import errorBarsPlugin from 'chartjs-plugin-error-bars';

import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/percent';

import { deepEquals, filterObject } from '@/utils';

import { BarChart, ScatterPlot } from '@/components/Charts';
import DatetimePicker from '@/components/DatetimePicker';
import DescriptionPopover from '@/components/DescriptionPopover';

export default {
    name: 'analytics-rubric-stats',

    props: {
        value: {
            type: Object,
            default: {},
        },
        filterResults: {
            type: Array,
            required: true,
        },
    },

    data() {
        return {
            ...this.fillSettings(this.value),
        };
    },

    computed: {
        filterLabels() {
            return this.filterResults.map(f => f.filter.toString());
        },

        assignment() {
            if (this.filterResults.length === 0) {
                return null;
            }
            return this.filterResults[0].workspace.assignment;
        },

        rubric() {
            return this.$utils.getProps(this.assignment, null, 'rubric');
        },

        metricOptions() {
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

        rubricSources() {
            return this.filterResults.map(r => r.getSource('rubric_data'));
        },

        rubricStatistics() {
            const baseStats = {
                mean: {
                    chartComponent: 'bar-chart',
                    data: this.getHistogramData('mean', this.relative),
                    options: this.histogramOptions,
                    hasRelative: true,
                },
                median: {
                    chartComponent: 'bar-chart',
                    data: this.getHistogramData('median', this.relative),
                    options: this.histogramOptions,
                    hasRelative: true,
                },
                mode: {
                    chartComponent: 'bar-chart',
                    data: this.getHistogramData('mode', this.relative),
                    options: this.histogramOptions,
                    hasRelative: true,
                },
                rit: {
                    chartComponent: 'bar-chart',
                    data: this.getHistogramData('rit'),
                    options: this.histogramOptions,
                },
                rir: {
                    chartComponent: 'bar-chart',
                    data: this.getHistogramData('rir'),
                    options: this.histogramOptions,
                },
            };

            this.rubric.rows.forEach(row => {
                baseStats[row.id] = {
                    chartComponent: 'scatter-plot',
                    data: this.getScatterData(row),
                    options: this.scatterOpts,
                };
            });

            return baseStats;
        },

        selectedStatistic() {
            if (this.metric == null) {
                return null;
            }
            return this.rubricStatistics[this.metric];
        },

        chartEmpty() {
            if (this.selectedStatistic == null) {
                return true;
            } else {
                return this.selectedStatistic.data.datasets.every(ds => ds.data.length === 0);
            }
        },

        normalizeFactors() {
            if (!this.relative) {
                return null;
            }
            return this.rubric.rows.map(row => [row.minPoints, row.maxPoints]);
        },

        histogramOptions() {
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
                ];
            };

            const labelString = this.metricOptions.find(
                so => so.value === this.metric,
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

        scatterOptions() {
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

        settings() {
            const defaults = this.fillSettings({});
            const settings = {
                relative: this.relative,
                metric: this.metric,
            };
            return filterObject(settings, (val, key) => !deepEquals(val, defaults[key]));
        },
    },

    methods: {
        fillSettings(settings) {
            return Object.assign({
                relative: true,
                metric: 'mean',
            }, settings);
        },

        resetParams() {
            Object.assign(this, this.fillSettings({}));
        },

        getHistogramData(key, normalize) {
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
                if (normalize && this.normalizeFactors != null) {
                    normalized = this.normalize(data, this.normalizeFactors);

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

        getScatterData(row) {
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
    },

    watch: {
        settings: {
            immediate: true,
            handler() {
                this.$emit('input', this.settings);
            },
        },
    },

    components: {
        Icon,
        BarChart,
        ScatterPlot,
        DatetimePicker,
        DescriptionPopover,
    },
};
</script>
