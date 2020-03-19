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

import { BarChart, ScatterPlot } from '@/components/Charts';
import { UNSET_SENTINEL } from '@/constants';
import { mapObject } from '@/utils';

function zip(...lists) {
    if (lists.length === 0) {
        return [];
    }

    const acc = [];
    const end = Math.max(...lists.map(l => l.length));
    for (let i = 0; i < end; i++) {
        // eslint-disable-next-line no-loop-func
        acc.push(lists.map(l => l[i]));
    }
    return acc;
}

function dropNull(xs) {
    return xs.filter(x => x != null);
}

function sum(xs) {
    return xs.reduce((x, y) => x + y, 0);
}

function normalize(xs) {
    const total = sum(xs);
    return xs.map(x => x / total);
}

function normalizePerc(xs) {
    return normalize(xs).map(x => 100 * x);
}

function mean(xs) {
    return sum(xs) / xs.length;
}

function stddev(xs, mu = mean(xs)) {
    const n = xs.length;
    return Math.sqrt(1 / (n - 1) * sum(xs.map(x => (x - mu) ** 2)));
}

// https://en.wikipedia.org/wiki/Pearson_correlation_coefficient#For_a_sample
function pearson(xs, ys) {
    if (!xs || xs.length < 10 || !ys || ys.length < 10) {
        return null;
    }

    const n = xs.length;
    const muX = mean(xs);
    const muY = mean(ys);
    const sX = stddev(xs, muX);
    const sY = stddev(ys, muY);

    return (sum(zip(xs, ys).map(sum)) - n * muX * muY) / ((n - 1) * sX * sY);
}

function objFromKeys(keys, value) {
    const v = () => (typeof value === 'function' ? value() : value);
    return Object.fromEntries(keys.map(k => [k, v()]));
}

class RubricResults {
    constructor(rubric, results) {
        this.rubric = rubric;
        this.rowIds = rubric.rows.map(row => row.id);
        this.results = results;

        this._cache = Object.seal({
            totalScorePerStudent: UNSET_SENTINEL,
            nTimesFilledPerCat: UNSET_SENTINEL,
            scoresPerStudent: UNSET_SENTINEL,
            ritItemsPerCat: UNSET_SENTINEL,
            rirItemsPerCat: UNSET_SENTINEL,
            scoresPerCat: UNSET_SENTINEL,
            meanPerCat: UNSET_SENTINEL,
            ritPerCat: UNSET_SENTINEL,
            rirPerCat: UNSET_SENTINEL,
        });
    }

    get scoresPerStudent() {
        if (this._cache.scoresPerStudent === UNSET_SENTINEL) {
            this._cache.scoresPerStudent = this.results.map(result =>
                mapObject(result.selected, item => item.achieved_points),
            );
        }
        return this._cache.scoresPerStudent;
    }

    get totalScorePerStudent() {
        if (this._cache.totalScorePerStudent === UNSET_SENTINEL) {
            this._cache.totalScorePerStudent = this.scoresPerStudent.map(result =>
                sum(dropNull(Object.values(result))),
            );
        }
        return this._cache.totalScorePerStudent;
    }

    get scoresPerCat() {
        if (this._cache.scoresPerCat === UNSET_SENTINEL) {
            this._cache.scoresPerCat = this.scoresPerStudent.reduce((acc, result) => {
                this.rowIds.forEach(rowId => acc[rowId].push(result[rowId]));
                return acc;
            }, objFromKeys(this.rowIds, () => []));
        }
        return this._cache.scoresPerCat;
    }

    get meanPerCat() {
        if (this._cache.meanPerCat === UNSET_SENTINEL) {
            this._cache.meanPerCat = mapObject(this.scoresPerCat, scores => {
                const mu = mean(dropNull(scores));
                return Number.isNaN(mu) ? 0 : mu;
            });
        }
        return this._cache.meanPerCat;
    }

    get ritItemsPerCat() {
        if (this._cache.ritItemsPerCat === UNSET_SENTINEL) {
            this._cache.ritItemsPerCat = this.rowIds.reduce((acc, rowId) => {
                acc[rowId] = zip(this.scoresPerCat[rowId], this.totalScorePerStudent).filter(
                    ([s]) => s != null,
                );
                return acc;
            }, {});
        }
        return this._cache.ritItemsPerCat;
    }

    get ritPerCat() {
        if (this._cache.ritPerCat === UNSET_SENTINEL) {
            this._cache.ritPerCat = mapObject(this.ritItemsPerCat, catScores =>
                pearson(...zip(...catScores)),
            );
        }
        return this._cache.ritPerCat;
    }

    get rirItemsPerCat() {
        if (this._cache.rirItemsPerCat === UNSET_SENTINEL) {
            this._cache.rirItemsPerCat = mapObject(this.ritItemsPerCat, catScores =>
                catScores.map(([itemScore, totalScore]) => [itemScore, totalScore - itemScore]),
            );
        }
        return this._cache.rirItemsPerCat;
    }

    get rirPerCat() {
        if (this._cache.rirPerCat === UNSET_SENTINEL) {
            this._cache.rirPerCat = mapObject(this.rirItemsPerCat, catScores =>
                pearson(...zip(...catScores)),
            );
        }
        return this._cache.rirPerCat;
    }

    get nTimesFilledPerCat() {
        if (this._cache.nTimesFilledPerCat === UNSET_SENTINEL) {
            this._cache.nTimesFilledPerCat = mapObject(
                this.scoresPerCat,
                scores => dropNull(scores).length,
            );
        }
        return this._cache.nTimesFilledPerCat;
    }
}

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
            return mean(this.submissionGrades);
        },

        gradeHistogram() {
            const bins = [...Array(10).keys()].map(x => [x, x + 1]);
            const binned = this.binSubmissionsByGrade(bins);
            const labels = bins.map(([start, end]) => `${10 * start}% - ${10 * end}%`);

            const datasets = [
                {
                    label: 'Percentage of students',
                    data: normalizePerc(binned.map(subs => subs.length)),
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
            const toNDec = x => (Number.isFinite(x) ? this.$utils.toMaxNDecimals : '-');

            // const label = tooltipItem => `Mean score: ${toNDec(tooltipItem.yLabel, 2)}`;
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
                    `Rit: ${toNDec(rit, 2)}`,
                    `Rir: ${toNDec(rir, 2)}`,
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
