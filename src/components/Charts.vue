<script>
import { Bar, Scatter, mixins } from 'vue-chartjs';

export const BarChart = {
    name: 'bar-chart',
    extends: Bar,
    mixins: [mixins.reactiveProp],

    props: {
        options: {
            type: Object,
            default: () => ({}),
        },
    },

    mounted() {
        this.renderChart(this.chartData, this.options);
    },
};

export const ScatterPlot = {
    name: 'scatter-plot',
    extends: Scatter,
    mixins: [mixins.reactiveProp],

    props: {
        options: {
            type: Object,
            default: () => ({}),
        },
    },

    mounted() {
        this.renderChart(this.chartData, this.options);
    },
};
</script>
