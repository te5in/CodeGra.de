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
            // If subclasses need to do some processing on the data they have
            // received in their props they can do that here.

            return this.chartData;
        },

        renderOpts() {
            // If subclasses need to do some processing on the options they
            // have received in their props they can do that here.

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
            return {
                legend: {
                    labels: {
                        fontColor: this.darkModeColor(1),
                    },
                },
                scales: {
                    xAxes: [
                        {
                            gridLines: {
                                color: this.darkModeColor(0.2),
                                zeroLineColor: this.darkModeColor(0.6),
                            },
                            scaleLabel: {
                                fontColor: this.darkModeColor(0.8),
                            },
                            ticks: {
                                fontColor: this.darkModeColor(0.8),
                            },
                        },
                    ],
                    yAxes: [
                        {
                            gridLines: {
                                color: this.darkModeColor(0.2),
                                zeroLineColor: this.darkModeColor(0.6),
                            },
                            scaleLabel: {
                                fontColor: this.darkModeColor(0.8),
                            },
                            ticks: {
                                fontColor: this.darkModeColor(0.8),
                            },
                        },
                    ],
                },
            };
        },

        colorPairs() {
            const pairs = COLOR_PAIRS.map(p => Object.assign({}, p));

            if (this.darkMode) {
                pairs[0].background = this.darkModeColor(1);
            }

            return pairs;
        },
    },

    methods: {
        rerender() {
            this.renderChart(this.renderData, this.renderOpts);
        },

        getColors(n_) {
            const colors = this.colorPairs.map(c => this.processColor(c.background));
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

        darkModeColor(alpha) {
            // This is @text-color-dark from mixins.less.
            if (alpha === 1) {
                return 'rgb(210, 212, 213)';
            } else {
                return `rgb(210, 212, 213, ${alpha})`;
            }
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

            const factor = 1 + this.padding;
            const min = factor * stat.min(this.minPerDataset);
            const max = factor * stat.max(this.maxPerDataset);

            return [Math.min(0, min), Math.max(0, max)];
        },

        valuesPerDataset() {
            // Get the values per dataset that need to be considered for the
            // calculation of the limits, i.e. add the error to the
            // corresponding data value for each data point.
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
            return this.valuesPerDataset.map(
                values => (values.length === 0 ? 0 : stat.min(values)),
            );
        },

        maxPerDataset() {
            return this.valuesPerDataset.map(
                values => (values.length === 0 ? 0 : stat.max(values)),
            );
        },
    },

    methods: {
        errors(dataset) {
            // Convert the errorBars object on a dataset to an array of error
            // values in the same order as the data array on the dataset.
            const errors = dataset.errorBars;
            if (errors == null) {
                return null;
            }
            return this.chartData.labels.map(label => dataset.errorBars[label]);
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
