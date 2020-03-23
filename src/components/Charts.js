/* SPDX-License-Identifier: AGPL-3.0-only */
import { Bar, Scatter, mixins } from 'vue-chartjs';
import * as stat from 'simple-statistics';

import { mapGetters } from 'vuex';

import { COLOR_PAIRS } from '@/constants';
import { mapObject } from '@/utils';

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
        redToGreen: {
            type: Boolean,
            default: false,
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
            if (this.redToGreen) {
                return this.redToGreenGradient(n_);
            }

            // TODO: get colors based on a hash
            const colors = COLOR_PAIRS.map(c => c.background);
            const ret = [];

            let n = n_;
            while (n > 0) {
                const add = colors.slice(0, n);
                ret.push(...add);
                n -= add.length;
            }

            return this.processColors(ret);
        },

        redToGreenGradient(n) {
            const range = this.$utils.range;

            const nRed = Math.floor(n / 2);
            const nGreen = n - nRed;

            const reds = [].concat(
                range(nRed).map(() => 255),
                range(nGreen).map(i => (nGreen - i) / nGreen * 255),
            );
            const greens = [].concat(
                range(nRed).map(i => i / nRed * 255),
                range(nGreen).map(() => 255),
            );

            return this.processColors(range(n).map(i => `rgb(${reds[i]}, ${greens[i]}, 0)`));
        },

        processColors(colors) {
            return {
                backgroundColor: colors.map(clr => clr.replace(')', ', 0.6)')),
                hoverBackgroundColor: colors.map(clr => clr.replace(')', ', 0.8)')),
                borderColor: colors,
                borderWidth: colors.map(() => 2),
            };
        },
    },

    watch: {
        options() {
            this.rerender();
        },

        renderOptions() {
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

    props: {
        relativeTo: {
            type: [Array, Number],
            default: null,
        },
    },

    computed: {
        renderData() {
            return Object.assign({}, this.chartData, {
                datasets: this.datasets.map(ds => {
                    let data = ds.data;
                    if (this.relativeTo != null) {
                        data = this.normalize(data);
                    }
                    return Object.assign({}, ds, {
                        data,
                        minBarLength: 3,
                    }, this.getColors(data.length));
                }),
            });
        },

        renderOpts() {
            const [min, max] = this.suggestedRange;
            return this.$utils.deepExtendArray(this.baseOptions, {
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
            }, this.options);
        },

        suggestedRange() {
            const factor = 1 + this.padding;
            const minPerCat = this.datasets.map(ds => stat.min(ds.data));
            const maxPerCat = this.datasets.map(ds => stat.max(ds.data));
            return [
                factor * stat.min(minPerCat),
                factor * stat.max(maxPerCat),
            ];
        },
    },

    watch: {
        relativeTo() {
            this.rerender();
        },
    },

    methods: {
        normalize(xs) {
            const rel = this.relativeTo;

            if (typeof rel === 'number') {
                return xs.map(x => 100 * x / rel);
            } else if (Array.isArray(rel)) {
                return xs.map((x, i) => 100 * this.normalize1(x, rel[i]));
            } else {
                return xs;
            }
        },

        normalize1(x, [lower, upper]) {
            return x <= 0 ? -x / lower : x / upper;
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
            return Object.assign({}, this.chartData, {
                datasets: this.datasets.map((ds, i) =>
                    Object.assign({}, ds, mapObject(colors, l => l[i])),
                ),
            });
        },

        renderOpts() {
            return this.$utils.deepExtendArray(this.baseOptions, {
                scales: {
                    xAxes: [
                        {
                            ticks: this.suggestedXRange,
                        },
                    ],
                    yAxes: [
                        {
                            ticks: this.suggestedYRange,
                        },
                    ],
                },
            }, this.options);
        },

        suggestedXRange() {
            return this.suggestedRange('x');
        },

        suggestedYRange() {
            return this.suggestedRange('y');
        },
    },

    methods: {
        suggestedRange(dim) {
            const xsPerDataset = this.datasets.map(ds => ds.data.map(el => el[dim]));
            const xs = [].concat(...xsPerDataset);

            const minX = stat.min(xs);
            const maxX = stat.max(xs);
            const dX = maxX - minX;

            return {
                suggestedMin: minX - this.padding * dX || 0,
                suggestedMax: maxX + this.padding * dX || 1,
            };
        },
    },
};
