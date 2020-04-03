/* SPDX-License-Identifier: AGPL-3.0-only */
import { Bar, Scatter, mixins } from 'vue-chartjs';
import * as stat from 'simple-statistics';

import { mapGetters } from 'vuex';

import { COLOR_PAIRS } from '@/constants';

export const BaseChart = {
    props: {
        options: {
            type: Object,
            default: () => ({}),
        },
        padding: {
            type: Number,
            default: 0.2,
        },
    },

    computed: {
        ...mapGetters('pref', ['darkMode']),

        datasets() {
            return this.chartData.datasets;
        },

        renderData() {
            return this.chartData;
        },

        renderOpts() {
            return this.options;
        },

        baseOptions() {
            const baseOpts = {
                legend: {
                    fullWidth: true,
                    align: 'end',
                    labels: {
                        boxWidth: 12,
                    },
                },
                tooltips: {
                    cornerRadius: 4,
                    xPadding: 12,
                    yPadding: 8,
                },
            };

            if (this.darkMode) {
                Object.assign(baseOpts, this.darkModeOpts);
            }

            return baseOpts;
        },

        darkModeOpts() {
            // This is @text-color-dark from mixins.less.
            const color = alpha => `rgb(210, 212, 213, ${alpha})`;

            return {
                legend: {
                    labels: {
                        fontColor: color(1),
                    },
                },
                scales: {
                    xAxes: [
                        {
                            gridLines: {
                                color: color(0.2),
                                zeroLineColor: color(0.6),
                            },
                            scaleLabel: {
                                fontColor: color(0.8),
                            },
                            ticks: {
                                fontColor: color(0.8),
                            },
                        },
                    ],
                    yAxes: [
                        {
                            gridLines: {
                                color: color(0.2),
                                zeroLineColor: color(0.6),
                            },
                            scaleLabel: {
                                fontColor: color(0.8),
                            },
                            ticks: {
                                fontColor: color(0.8),
                            },
                        },
                    ],
                },
            };
        },
    },

    methods: {
        rerender() {
            this.renderChart(this.renderData, this.renderOpts);
        },

        getColors(n_) {
            const colors = COLOR_PAIRS.map(c => this.processColor(c.background));
            const ret = [];

            let n = n_;
            while (n > 0) {
                const add = colors.slice(0, n);
                ret.push(...add);
                n -= add.length;
            }

            return ret;
        },

        processColor(color) {
            return {
                backgroundColor: color.replace(')', ', 0.6)'),
                hoverBackgroundColor: color.replace(')', ', 0.8)'),
                borderColor: color,
                borderWidth: 2,
                lineColor: color.replace(')', ', 0.4)'),
            };
        },
    },

    watch: {
        options() {
            this.rerender();
        },

        renderData() {
            this.rerender();
        },

        renderOptions() {
            this.rerender();
        },

        darkMode() {
            this.rerender();
        },
    },

    mounted() {
        this.rerender();
    },
};

export const BarChart = {
    name: 'bar-chart',
    extends: Bar,
    mixins: [mixins.reactiveProp, BaseChart],

    computed: {
        renderData() {
            const colors = this.getColors(this.datasets.length);
            const datasets = this.datasets.map((ds, i) =>
                Object.assign({}, ds, {
                    minBarLength: 3,
                    ...colors[i],
                }),
            );

            return Object.assign({}, this.chartData, { datasets });
        },

        renderOpts() {
            const [min, max] = this.suggestedRange;
            return this.$utils.deepExtendArray(
                this.baseOptions,
                {
                    scales: {
                        yAxes: [
                            {
                                ticks: {
                                    suggestedMin: min,
                                    suggestedMax: max,
                                },
                            },
                        ],
                    },
                },
                this.options,
            );
        },

        suggestedRange() {
            if (this.datasets.length === 0) {
                return [0, 0];
            }

            const min = stat.min(this.minPerDataset);
            const max = stat.max(this.maxPerDataset);

            const factor = 1 + this.padding;
            return [factor * min, factor * max];
        },

        valuesPerDataset() {
            return this.datasets.map(ds => {
                const errors = this.errors(ds);
                if (errors == null) {
                    return ds.data;
                }
                return ds.data.map((x, i) => {
                    const err = errors[i] || 0;
                    return x < 0 ? x + err.minus : x + err.plus;
                });
            });
        },

        minPerDataset() {
            return this.valuesPerDataset.map(values =>
                (values.length === 0 ? 0 : stat.min(values)),
            );
        },

        maxPerDataset() {
            return this.valuesPerDataset.map(values =>
                (values.length === 0 ? 0 : stat.max(values)),
            );
        },
    },

    methods: {
        errors(dataset) {
            const errors = dataset.errorBars;
            if (errors == null) {
                return null;
            }
            return this.chartData.labels.map(
                label => dataset.errorBars[label],
            );
        },
    },
};

export const ScatterPlot = {
    name: 'scatter-plot',
    extends: Scatter,
    mixins: [mixins.reactiveProp, BaseChart],

    computed: {
        renderData() {
            const colors = this.getColors(this.datasets.length);
            const datasets = this.datasets.map((ds, i) => Object.assign({}, ds, colors[i]));

            if (this.$utils.getProps(this.options, false, 'cgScatter', 'withBestFit')) {
                datasets.push(...datasets.map(this.fitLine).filter(x => x != null));
            }

            return Object.assign({}, this.chartData, { datasets });
        },

        renderOpts() {
            return this.$utils.deepExtendArray(
                this.baseOptions,
                {
                    scales: {
                        xAxes: [
                            {
                                ticks: this.xRange,
                            },
                        ],
                        yAxes: [
                            {
                                ticks: this.yRange,
                            },
                        ],
                    },
                },
                this.options,
            );
        },

        xRange() {
            return this.range('x');
        },

        yRange() {
            return this.range('y');
        },

        emptyRange() {
            return [0, 0];
        },
    },

    methods: {
        range(dim) {
            if (this.datasets.length === 0) {
                return this.emptyRange;
            }

            const xsPerDataset = this.datasets.map(ds => ds.data.map(el => el[dim]));
            const xs = [].concat(...xsPerDataset);

            if (xs.length === 0) {
                return this.emptyRange;
            }

            const minX = stat.min(xs);
            const maxX = stat.max(xs);
            const dX = maxX - minX;

            return {
                min: Math.floor(minX - this.padding * dX || 0),
                max: Math.ceil(maxX + this.padding * dX || 1),
            };
        },

        fitLine(dataset) {
            if (dataset.data.length === 0) {
                return null;
            }

            const { data } = dataset;
            const points = data.map(({ x, y }) => [x, y]);

            if (points.length === 0) {
                return null;
            }

            const f = stat.linearRegressionLine(stat.linearRegression(points));

            let { min, max } = this.xRange;
            // Make sure the endpoints of the line
            // are out of view.
            min -= max - min;
            max += max - min;

            return Object.assign({}, dataset, {
                type: 'line',
                label: `${dataset.label} (Best fit)`,
                data: [{ x: min, y: f(min) }, { x: max, y: f(max) }],
                backgroundColor: 'transparent',
                borderColor: dataset.lineColor,
            });
        },
    },
};
