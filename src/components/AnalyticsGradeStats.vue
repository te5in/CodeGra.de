<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<b-card class="analytics-grade-stats"
        header-class="d-flex">
    <template #header>
        <div class="flex-grow-1">
            Grade statistics
        </div>

        <div class="d-flex flex-grow-0">
            <b-button :variant="settings.relative ? 'primary' : 'outline-primary'"
                      @click="toggleRelative()"
                      v-b-popover.top.hover="relativePopoverText"
                      class="ml-3">
                <icon name="percent" />
            </b-button>

            <b-input-group class="mb-0">
                <input :value="settings.binSize"
                       @input="updateBinSize"
                       type="number"
                       min="0.5"
                       step="0.5"
                       class="form-control ml-2 pt-1"
                       style="max-width: 4rem;"/>
            </b-input-group>

            <description-popover class="icon-button ml-1"
                                 placement="bottom"
                                 :scale="1">
                <p class="mb-2">
                    The grade histogram shows the amount of students that got
                    a certain grade for this assignment. You can change the bin
                    size; fractional numbers are supported.
                </p>

                <p>
                    See
                    <a href="https://docs.codegra.de/user/analytics-dashboard.html#grade-statistics"
                       target="_blank"
                        >the documentation</a>
                    for more details.
                </p>
            </description-popover>
        </div>
    </template>

    <bar-chart :chart-data="histogramData"
               :options="histogramOptions"
               :width="300"
               :height="100"/>
</b-card>
</template>

<script>
import * as stat from 'simple-statistics';

import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/percent';

import { deepEquals, filterObject } from '@/utils';

import { BarChart } from '@/components/Charts';
import DescriptionPopover from '@/components/DescriptionPopover';

function fillSettings(settings) {
    return Object.assign(
        {
            relative: true,
            binSize: 0.5,
        },
        settings,
    );
}

export default {
    name: 'analytics-grade-stats',

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

            // Changing the submission date bin size can cause a lot of
            // bins to be drawn, especially when typing something like
            // `10`, where the value is temporarily `1`. We debounce the
            // event of the bin size input with this timer to prevent
            // temporary page freezes or flickering of the "too many bins"
            // message when editing the bin size.
            binSizeTimer: null,
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

        submissionSources() {
            return this.filterResults.map(r => r.submissions);
        },

        relativePopoverText() {
            if (this.settings.relative) {
                return 'Show amount of students in filter group';
            } else {
                return 'Show percentage of students of filter group';
            }
        },

        // TODO: Move this to a FilterResultSet model.
        histogramData() {
            const maxGrade = this.assignment.maxGrade;
            let binSize = parseFloat(this.settings.binSize);
            if (Number.isNaN(binSize)) {
                binSize = 1;
            }

            const bins = this.$utils.range(0, Math.ceil(maxGrade / binSize));
            const labels = bins.map(i => {
                if (binSize === 1) {
                    return i;
                }
                const start = this.to2Dec(i * binSize);
                const end = this.to2Dec(Math.min(maxGrade, (i + 1) * binSize));
                return `${start} - ${end}`;
            });

            const datasets = this.submissionSources.map((source, i) => {
                const data = source.binSubmissionsByGrade(binSize, maxGrade);

                const absData = bins.map(bin => data[bin].length);
                // We can't use source.submissionCount here, because some submissions
                // may have been filtered out, e.g. submissions without a grade.
                const nSubs = stat.sum(bins.map(bin => data[bin].length));
                const relData = absData.map(d => (nSubs ? 100 * d / nSubs : 0));

                return {
                    label: this.filterLabels[i],
                    absData,
                    relData,
                    data: this.settings.relative ? relData : absData,
                };
            });

            return { labels, datasets };
        },

        histogramOptions() {
            const getDataset = (tooltipItem, data) => data.datasets[tooltipItem.datasetIndex];

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

            const labelString = this.settings.relative
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
    },

    methods: {
        resetParams() {
            this.settings = fillSettings({});
        },

        toggleRelative() {
            this.updateSetting('relative', !this.settings.relative);
        },

        updateBinSize(event) {
            clearTimeout(this.binSizeTimer);
            this.binSizeTimer = setTimeout(() => {
                const newSize = parseFloat(event.target.value);
                if (!Number.isNaN(newSize) && newSize !== this.settings.binSize && newSize > 0) {
                    this.updateSetting('binSize', newSize);
                }
            }, 500);
        },

        updateSetting(name, value) {
            if (!this.$utils.hasAttr(this.settings, name)) {
                throw new Error(`Invalid setting: ${name}`);
            }
            this.settings = Object.assign({}, this.settings, { [name]: value });
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
    },

    components: {
        Icon,
        BarChart,
        DescriptionPopover,
    },
};
</script>
