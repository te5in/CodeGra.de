<template>
<b-card class="analytics-submission-count"
        header-class="d-flex">
    <template #header>
        <div class="flex-grow-1">
            Students submitted this many times
        </div>

        <div class="d-flex flex-grow-0">
            <b-button :variant="relative ? 'primary' : 'outline-primary'"
                      @click="relative = !relative"
                      v-b-popover.top.hover="'Relative to filter group'"
                      class="ml-3">
                <icon name="percent" />
            </b-button>

            <description-popover class="icon-button ml-1"
                                 placement="bottom"
                                 :scale="1">
                <p class="mb-2">
                    This histogram shows the amount of times students submitted
                    their work.
                </p>

                <p>
                    See
                    <a href="https://docs.codegra.de/user/analytics-dashboard.html#submission-statistics"
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
               :height="$root.$isXLargeWindow ? 75 : 100"/>
</b-card>
</template>

<script>
import * as stat from 'simple-statistics';

import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/percent';

import { deepEquals, filterObject } from '@/utils';

import { BarChart } from '@/components/Charts';
import DescriptionPopover from '@/components/DescriptionPopover';

export default {
    name: 'analytics-submission-count',

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

        submissionSources() {
            return this.filterResults.map(r => r.submissions);
        },

        histogramData() {
            const subsPerStudent = this.submissionSources.map(source =>
                source.submissionsPerStudent,
            );

            const max = stat.max(subsPerStudent.map(s =>
                stat.max(Object.keys(s).map(Number)),
            ));
            const labels = this.$utils.range(1, max + 1);

            const datasets = subsPerStudent.map((data, i) => {
                const absData = labels.map(nSubs => data[nSubs]);
                const nStudents = stat.sum(Object.values(data));
                const relData = absData.map(x => (100 * x) / nStudents);

                return {
                    label: this.filterLabels[i],
                    data: this.relative ? relData : absData,
                    absData,
                    relData,
                };
            });

            return { labels, datasets };
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
                const abs = ds.absData[tooltipItem.index];
                const rel = ds.relData[tooltipItem.index];

                // Do not escape, chart.js does its own escaping.
                return [
                    `Number of students: ${abs}`,
                    `Percentage of students: ${this.to2Dec(rel)}`,
                ];
            };

            const labelString = this.relative
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

        settings() {
            const defaults = this.fillSettings({});
            const settings = {
                relative: this.relative,
            };

            return filterObject(settings, (val, key) => !deepEquals(val, defaults[key]));
        },
    },

    methods: {
        fillSettings(settings) {
            return Object.assign({
                relative: true,
            }, settings);
        },

        resetParams() {
            Object.assign(this, this.fillSettings({}));
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
        DescriptionPopover,
    },
};
</script>

<style lang="less" scoped>
</style>
