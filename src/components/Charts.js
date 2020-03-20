/* SPDX-License-Identifier: AGPL-3.0-only */
import { Bar, Scatter, mixins } from 'vue-chartjs';

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
        datasets() {
            return this.chartData.datasets;
        },

        renderData() {
            return this.chartData;
        },

        renderOpts() {
            return this.options;
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
                    return Object.assign({}, ds, { data }, this.getColors(data.length));
                }),
            });
        },

        renderOpts() {
            return this.$utils.deepExtendArray({
                scales: {
                    yAxes: [
                        {
                            ticks: {
                                beginAtZero: true,
                                suggestedMax: this.suggestedMax,
                            },
                        },
                    ],
                },
            }, this.options);
        },

        suggestedMax() {
            const factor = 1 + this.padding;
            const maxPerCat = this.datasets.map(ds => Math.max(...ds.data));
            return factor * Math.max(...maxPerCat);
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
                return xs.map((x, i) => 100 * x / rel[i]);
            } else {
                return xs;
            }
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
            return this.$utils.deepExtendArray({
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

            const minX = Math.min(...xs);
            const maxX = Math.max(...xs);
            const dX = maxX - minX;

            return {
                suggestedMin: minX - this.padding * dX || 0,
                suggestedMax: maxX + this.padding * dX || 1,
            };
        },
    },
};
