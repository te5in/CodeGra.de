<!-- SPDX-License-Identifier: AGPL-3.0-only -->
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
                      :variant="settings.relative ? 'primary' : 'outline-primary'"
                      @click="toggleRelative"
                      v-b-popover.top.hover="relativePopoverText">
                <icon name="percent" />
            </b-button>

            <b-form-select :value="settings.metric"
                           @input="updateMetric"
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

    <loader v-else-if="rerendering" />

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
import Loader from '@/components/Loader';
import DatetimePicker from '@/components/DatetimePicker';
import DescriptionPopover from '@/components/DescriptionPopover';

function fillSettings(settings) {
    return Object.assign(
        {
            relative: true,
            metric: 'mean',
        },
        settings,
    );
}

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
            settings: fillSettings(this.value),

            rerendering: false,
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
            if (this.settings.relative) {
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
                    data: this.getHistogramData('mean', this.settings.relative),
                    options: this.histogramOptions,
                    hasRelative: true,
                },
                median: {
                    chartComponent: 'bar-chart',
                    data: this.getHistogramData('median', this.settings.relative),
                    options: this.histogramOptions,
                    hasRelative: true,
                },
                mode: {
                    chartComponent: 'bar-chart',
                    data: this.getHistogramData('mode', this.settings.relative),
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
            if (this.settings.metric == null) {
                return null;
            }
            return this.rubricStatistics[this.settings.metric];
        },

        chartEmpty() {
            if (this.selectedStatistic == null) {
                return true;
            } else {
                return this.selectedStatistic.data.datasets.every(ds => ds.data.length === 0);
            }
        },

        normalizeFactors() {
            if (!this.settings.relative) {
                return null;
            }
            return this.rubric.rows.map(row => [row.minPoints, row.maxPoints]);
        },

        histogramOptions() {
            const getDataset = (tooltipItem, data) => data.datasets[tooltipItem.datasetIndex];

            const title = (tooltipItems, data) => {
                const tooltipItem = this.$utils.getProps(tooltipItems, null, 0);
                if (tooltipItem == null) {
                    return '';
                }

                const ds = getDataset(tooltipItem, data);
                const rubricLockReason = this.$utils.getProps(
                    ds,
                    null,
                    'stats',
                    tooltipItem.index,
                    'rubricRow',
                    'locked',
                );

                switch (rubricLockReason) {
                    case 'auto_test':
                        return `${tooltipItem.label} (AutoTest)`;
                    default:
                        return tooltipItem.label;
                }
            };

            const label = (tooltipItem, data) => {
                const ds = getDataset(tooltipItem, data);
                return ds.label;
            };

            const numOrDash = x => (x == null ? '-' : this.to2Dec(x));

            const afterLabel = (tooltipItem, data) => {
                const ds = getDataset(tooltipItem, data);
                const stats = ds.stats[tooltipItem.index];

                // Do not escape, chart.js does its own escaping.
                return [
                    `Max. points: ${stats.rubricRow.maxPoints}`,
                    `Times filled: ${stats.nTimesFilled}`,
                    `Mean: ${numOrDash(stats.mean)}`,
                    `Std. deviation: ${numOrDash(stats.stdev)}`,
                    `Median: ${numOrDash(stats.median)}`,
                    `Mode: ${numOrDash(stats.mode)}`,
                    `Rit: ${numOrDash(stats.rit) || '-'}`,
                    `Rir: ${numOrDash(stats.rir) || '-'}`,
                ];
            };

            const labelString = this.metricOptions.find(so => so.value === this.settings.metric)
                .text;

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
                    callbacks: { title, label, afterLabel },
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
    },

    methods: {
        resetParams() {
            this.settings = fillSettings({});
        },

        toggleRelative() {
            this.updateSetting('relative', !this.settings.relative);
        },

        updateMetric(metric) {
            this.updateSetting('metric', metric);
        },

        updateSetting(name, value) {
            if (!this.$utils.hasAttr(this.settings, name)) {
                throw new Error(`Invalid setting: ${name}`);
            }
            this.settings = Object.assign({}, this.settings, { [name]: value });
        },

        forceRerender() {
            this.rerendering = true;
            this.$afterRerender(() => {
                this.rerendering = false;
            });
        },

        // TODO: Move this to a FilterResultSet model.
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
                        rubricRow: row,
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
                        errorBars = stats.map(({ stdev }, j) => {
                            if (stdev == null) {
                                return null;
                            } else {
                                return normalized[j] / data[j] * stdev;
                            }
                        });
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
            if (Array.isArray(factors)) {
                return xs.map((x, i) => 100 * this.normalize1(x, factors[i]));
            } else {
                return xs;
            }
        },

        normalize1(x, [lower, upper]) {
            if (x === 0) {
                return 0;
            }
            if (lower === upper) {
                return x === 0 ? 0 : 1;
            }
            // If x < 0 then lower must also be, because you can't score less
            // than the least amount of points.
            if (x < 0) {
                return -x / lower;
            }

            return x / upper;
        },

        to2Dec(x) {
            return this.$utils.toMaxNDecimals(x, 2);
        },
    },

    watch: {
        settings: {
            immediate: true,
            handler() {
                const defaults = fillSettings({});
                const settings = filterObject(
                    this.settings,
                    (val, key) => !deepEquals(val, defaults[key]),
                );
                this.$emit('input', settings);
            },
        },

        filterResults() {
            this.forceRerender();
        },
    },

    components: {
        Icon,
        Loader,
        BarChart,
        ScatterPlot,
        DatetimePicker,
        DescriptionPopover,
    },
};
</script>
