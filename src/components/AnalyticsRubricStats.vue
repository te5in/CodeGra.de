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
                      v-b-popover.top.hover="relativePopoverText">
                <icon name="percent" />
            </b-button>

            <b-form-select v-model="metric"
                           :options="metricOptions"
                           class="ml-2"
                           style="max-width: 7.5rem"/>

            <description-popover class="icon-button ml-1"
                                 placement="bottom"
                                 :scale="1">
                <p class="mb-2">
                    This is a collection of several diagrams showing how
                    students scored in each rubric category, as well as diagrams
                    measuring the quality of the rubric categories.
                </p>

                <p>
                    See
                    <a href="https://docs.codegra.de/user/analytics-dashboard.html#rubric-statistics"
                       target="_blank"
                        >the documentation</a>
                    for more details.
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

        relativePopoverText() {
            if (this.relative) {
                return 'Show amount of points';
            } else {
                return 'Show percentage of points relative to the maximum score in the category';
            }
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
                    options: this.scatterOptions,
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
            const getDataset = (tooltipItem, data) => data.datasets[tooltipItem.datasetIndex];

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
                    `Mode: ${this.to2Dec(stats.mode)}`,
                    `Rit: ${this.to2Dec(stats.rit) || '-'}`,
                    `Rir: ${this.to2Dec(stats.rir) || '-'}`,
                ];
            };

            const labelString = this.metricOptions.find(so => so.value === this.metric).text;

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
            return Object.assign(
                {
                    relative: true,
                    metric: 'mean',
                },
                settings,
            );
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
                        errorBars = stats.map(({ stdev }, j) => normalized[j] / data[j] * stdev);
                    }
                }

                if (errorBars != null) {
                    errorBars = errorBars.reduce((acc, stdev, j) => {
                        acc[labels[j]] = { plus: stdev, minus: -stdev };
                        return acc;
                    }, {});
                }

                return {
                    label: this.filterLabels[i],
                    data: normalized,
                    stats,
                    errorBars,
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
