<template>
<div class="analytics-dashboard row">
    <div class="col-12">
        <b-card header="General statistics">
            <div class="row">
                <div class="col-3 border-right metric">
                    <h1>{{ latestSubmissions.length }}</h1>
                    <label>Number of students</label>
                </div>

                <div class="col-3 border-right metric">
                    <h1>{{ $utils.toMaxNDecimals(averageGrade, 2) }}</h1>
                    <label>Average grade</label>
                </div>

                <div class="col-3 border-right metric">
                    <h1 title="Not yet implemented">?</h1>
                    <label>Average Number of submissions</label>
                </div>

                <div class="col-3 metric">
                    <h1 title="Not yet implemented">?</h1>
                    <label>Average Number of feedback entries</label>
                </div>
            </div>
        </b-card>
    </div>

    <div class="col-12 col-lg-6"
         :class="{ 'col-lg-12': largeGradeHistogram }">
        <b-card header="Histogram of grades">
            <bar-chart :chart-data="gradeHistogram"
                       red-to-green
                       :width="300"
                       :height="largeGradeHistogram ? 100 : 200"/>
        </b-card>
    </div>

    <template v-if="hasRubric && rubricResults != null">
        <div class="col-12 col-lg-6"
             :class="{ 'col-lg-12': hasManyRubricRows }">
            <b-card header="Mean score per rubric category">
                <bar-chart :chart-data="rubricMeanHistogram"
                           :options="rubricMeanHistOpts"
                           :width="300"
                           :height="largeGradeHistogram ? 100 : 200"/>
            </b-card>
        </div>

        <template v-for="row in rubric.rows">
            <div class="col-12 col-lg-6">
                <b-card :header="`${row.header}: Correlation of item score vs. total score`">
                    <scatter-plot :chart-data="rubricCatScatter[row.id]"
                                  :options="rubricCatScatterOpts[row.id]"
                                  :width="300"
                                  :height="200"/>
                </b-card>
            </div>
        </template>
    </template>
</div>
</template>

<script>
import { mapGetters } from 'vuex';
import jStat from 'jstat';

import { RubricResults } from '@/models';
import { BarChart, ScatterPlot } from '@/components/Charts';

export default {
    name: 'analytics-dashboard',

    props: {
        assignmentId: {
            type: Number,
            required: true,
        },
    },

    computed: {
        ...mapGetters('courses', ['assignments']),
        ...mapGetters('submissions', ['getLatestSubmissions']),
        ...mapGetters('rubrics', { allRubricResults: 'results' }),

        assignment() {
            return this.assignments[this.assignmentId];
        },

        rubric() {
            return this.$utils.getProps(this.assignment, null, 'rubric');
        },

        hasRubric() {
            return this.rubric != null;
        },

        hasManyRubricRows() {
            return this.$utils.getProps(this.rubric, 0, 'rows', 'length') > 8;
        },

        largeGradeHistogram() {
            return !this.hasRubric || this.hasManyRubricRows;
        },

        latestSubmissions() {
            return this.getLatestSubmissions(this.assignmentId);
        },

        submissionGrades() {
            return this.latestSubmissions
                .map(sub => sub.grade)
                .filter(grade => grade != null)
                .map(grade => Number(grade));
        },

        averageGrade() {
            return jStat.mean(this.submissionGrades);
        },

        gradeHistogram() {
            const bins = [...Array(10).keys()].map(x => [x, x + 1]);
            const labels = bins.map(([start, end]) => `${10 * start}% - ${10 * end}%`);
            const binned = this.binSubmissionsByGrade(bins)
                .map(subs => subs.length / this.latestSubmissions.length);

            const datasets = [
                {
                    label: 'Percentage of students',
                    data: binned,
                },
            ];

            return { labels, datasets };
        },

        rubricResults() {
            if (this.rubric == null) {
                return null;
            }
            const results = this.latestSubmissions
                .map(sub => this.allRubricResults[sub.id])
                .filter(result => result != null);
            return new RubricResults(this.rubric, results);
        },

        rubricMeanHistogram() {
            if (this.rubric == null) {
                return null;
            }

            const labels = this.rubric.rows.map(row => row.header);
            const means = this.rubricResults.rowIds.map(
                rowId => this.rubricResults.meanPerCat[rowId],
            );

            const datasets = [
                {
                    label: 'Mean score',
                    data: means,
                },
            ];

            return { labels, datasets };
        },

        rubricMeanHistOpts() {
            const to2Dec = x => (Number.isFinite(x) ? this.$utils.toMaxNDecimals(x, 2) : '-');

            // const label = tooltipItem => `Mean score: ${to2Dec(tooltipItem.yLabel)}`;
            const label = () => '';

            const afterLabel = tooltipItem => {
                const {
                    rowIds,
                    meanPerCat,
                    ritPerCat,
                    rirPerCat,
                    nTimesFilledPerCat,
                } = this.rubricResults;

                const rowId = rowIds[tooltipItem.index];
                const mu = meanPerCat[rowId];
                const nTimes = nTimesFilledPerCat[rowId];
                const rit = ritPerCat[rowId];
                const rir = rirPerCat[rowId];

                // Do not escape, chart.js does its own escaping.
                return [
                    `Mean score: ${mu}`,
                    `Times filled: ${nTimes}`,
                    `Rit: ${to2Dec(rit)}`,
                    `Rir: ${to2Dec(rir)}`,
                    this.rirMessage(rir),
                ];
            };

            return {
                tooltips: {
                    callbacks: {
                        label,
                        afterLabel,
                    },
                },
            };
        },

        rubricCatScatter() {
            const results = this.rubricResults;

            return results.rowIds.reduce((acc, rowId) => {
                const ritItems = results.ritItemsPerCat[rowId].map(([x, y]) => ({ x, y }));
                const rirItems = results.rirItemsPerCat[rowId].map(([x, y]) => ({ x, y }));

                acc[rowId] = {
                    datasets: [
                        {
                            label: 'Rit',
                            data: ritItems,
                        },
                        {
                            label: 'Rir',
                            data: rirItems,
                        },
                    ],
                };
                return acc;
            }, {});
        },

        rubricCatScatterOpts() {
            return this.rubricResults.rowIds.reduce((acc, rowId) => {
                acc[rowId] = {
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
                                    labelString: 'Total score (minus item score for rir)',
                                },
                            },
                        ],
                    },
                };
                return acc;
            }, {});
        },
    },

    methods: {
        binSubmissionsBy(bins, f) {
            return this.latestSubmissions.reduce((acc, sub) => {
                const idx = bins.findIndex((bin, i) => f(sub, bin, i));
                if (idx !== -1) {
                    acc[idx].push(sub);
                }
                return acc;
            }, bins.map(() => []));
        },

        binSubmissionsByGrade(bins) {
            return this.binSubmissionsBy(bins, (sub, bin, i) => {
                const [low, high] = bin;
                const { grade } = sub;

                if (grade == null) {
                    return false;
                } else if (i === bins.length - 1) {
                    // Because we check the upper bound exclusively submissions
                    // with the highest possible grade will not be put in the last
                    // bin.
                    return true;
                } else {
                    return low <= grade && grade < high;
                }
            });
        },

        rirMessage(rir) {
            if (rir == null) {
                return 'There was not enough data to calculate a meaningful Rir value.';
            } else if (rir < 0) {
                return 'The rir value is negative, which means ...';
            } else if (rir > 0.25) {
                return 'The rir value is very high, which means...';
            } else {
                return 'The rir value is very close to zero, which means...';
            }
        },
    },

    components: {
        BarChart,
        ScatterPlot,
    },
};
</script>

<style lang="less" scoped>
.card {
    margin-bottom: 1rem;
}

.metric {
    text-align: center;

    label {
        padding: 0 1rem;
        margin-bottom: 0;
    }
}
</style>
