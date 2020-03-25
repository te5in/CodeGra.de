/* SPDX-License-Identifier: AGPL-3.0-only */
<template>
<div class="analytics-dashboard row">
    <loader page-loader v-if="loading" />

    <b-alert v-else-if="error"
             variant="danger"
             show>
        {{ $utils.getErrorMessage(error) }}
    </b-alert>

    <div v-else-if="baseSubmissionData.submissionCount === 0"
         class="col-12">
        <h3 class="border rounded p-5 text-center text-muted font-italic">
            There are no submissions yet.
        </h3>
    </div>

    <template v-else>
        <div class="col-12">
            <b-card header="General statistics"
                    body-class="pb-0">
                <div class="row">
                    <div class="col-6 col-md-3 mb-3 border-right metric">
                        <h1>{{ baseSubmissionData.studentCount }}</h1>
                        <label>Students</label>

                        <description-popover triggers="hover"
                                             placement="top">
                            Submitted a total of
                            {{ baseSubmissionData.submissionCount }} submissions!
                        </description-popover>
                    </div>

                    <div class="col-6 col-md-3 mb-3 metric"
                         :class="{ 'border-right': $root.$isMediumWindow }">
                        <h1>{{ to2Dec(latestSubmissionData.averageGrade) }}</h1>
                        <label>Average grade</label>

                        <description-popover triggers="hover"
                                             placement="top">
                            The average grade over the latest submissions.
                        </description-popover>
                    </div>

                    <hr v-if="!$root.$isMediumWindow"
                        class="w-100 mt-0 mx-3"/>

                    <div class="col-6 col-md-3 mb-3 border-right metric">
                        <h1>{{ to2Dec(baseSubmissionData.averageSubmissions) }}</h1>
                        <label>Average number of submissions</label>

                        <description-popover triggers="hover"
                                             placement="top">
                            The average number of submissions per student.
                        </description-popover>
                    </div>

                    <div class="col-6 col-md-3 mb-3 metric">
                        <h1>{{ to2Dec(latestInlineFeedbackSource.averageEntries) }}</h1>
                        <label>Average number of feedback entries</label>

                        <description-popover triggers="hover"
                                             placement="top">
                            The average number of feedback entries over the latest submissions.
                        </description-popover>
                    </div>
                </div>
            </b-card>

            <b-card header="Students submitted on">
                <bar-chart :chart-data="submissionDateHistogram"
                            :width="300"
                            :height="50"/>
            </b-card>
        </div>

        <div class="col-12">
            <b-card header="Filter sets">
                <div class="row">
                    <div v-for="filter, i in filters"
                         :key="i"
                         class="mb-3 col-6">
                        <div class="p-3 border rounded">
                            <b-input-group prepend="Latest">
                                <div class="form-control pl-2">
                                    <b-form-checkbox :checked="filter.onlyLatestSubs"
                                                     @input="updateFilter(i, 'onlyLatestSubs', $event)"
                                                     class="d-inline-block" />
                                    Only use latest submissions
                                </div>
                            </b-input-group>

                            <b-input-group prepend="Min. grade">
                                <input :value="filter.minGrade"
                                       @input="updateFilter(i, 'minGrade', $event.target.value)"
                                       class="form-control"
                                       type="number"
                                       placeholder="0"
                                       min="0"
                                       :max="filter.maxGrade"
                                       step="1" />

                                <template #append>
                                    <b-button variant="warning"
                                              :disabled="filter.minGrade == null"
                                              @click="updateFilter(i, 'minGrade', null)">
                                        <icon name="reply" />
                                    </b-button>
                                </template>
                            </b-input-group>

                            <b-input-group prepend="Max. grade">
                                <input :value="filter.maxGrade"
                                       @input="updateFilter(i, 'maxGrade', $event.target.value)"
                                       class="form-control"
                                       type="number"
                                       placeholder="10"
                                       :min="filter.minGrade"
                                       max="10"
                                       step="1" />

                                <template #append>
                                    <b-button variant="warning"
                                              :disabled="filter.maxGrade == null"
                                              @click="updateFilter(i, 'maxGrade', null)">
                                        <icon name="reply" />
                                    </b-button>
                                </template>
                            </b-input-group>

                            <b-input-group prepend="Submitted after">
                                <datetime-picker :value="filter.submittedAfter"
                                                 @input="updateFilter(i, 'submittedAfter', $event)"
                                                 :placeholder="`${assignmentCreated} (Assignment created)`"/>

                                <template #append>
                                    <b-button variant="warning"
                                              :disabled="filter.submittedAfter == null"
                                              @click="updateFilter(i, 'submittedAfter', null)">
                                        <icon name="reply" />
                                    </b-button>
                                </template>
                            </b-input-group>

                            <b-input-group prepend="Submitted before">
                                <datetime-picker :value="filter.submittedBefore"
                                                 @input="updateFilter(i, 'submittedBefore', $event)"
                                                 :placeholder="`${assignmentDeadline} (Assignment deadline)`"/>

                                <template #append>
                                    <b-button variant="warning"
                                              :disabled="filter.submittedBefore == null"
                                              @click="updateFilter(i, 'submittedAfter', null)">
                                        <icon name="reply" />
                                    </b-button>
                                </template>
                            </b-input-group>
                        </div>
                    </div>
                </div>

                <b-button variant="primary"
                          class="float-right"
                          @click="addFilter">
                    Add filter set
                </b-button>
            </b-card>
        </div>

        <div v-if="baseSubmissionData.submissionCount === 0"
            class="col-12">
            <h3 class="border rounded p-5 text-center text-muted font-italic">
                No submissions within the specified filter parameters.
            </h3>
        </div>

        <template v-else>
            <div class="col-12 col-lg-6"
                 :class="{ 'col-lg-12': largeGradeHistogram }">
                <b-card header="Histogram of grades">
                    <bar-chart :chart-data="gradeHistogram"
                               :width="300"
                               :height="largeGradeHistogram ? 100 : 200"/>
                </b-card>
            </div>

            <template v-if="hasRubricSource">
                <div class="col-12 col-lg-6"
                     :class="{ 'col-lg-12': largeGradeHistogram }">
                    <b-card header="Mean score per rubric category">
                        <bar-chart :chart-data="rubricMeanHistogram"
                                   :options="rubricMeanHistOpts"
                                   :relative-to="rubricNormalizeFactors"
                                   :width="300"
                                   :height="largeGradeHistogram ? 100 : 200"/>

                        <hr>

                        <b-input-group prepend="Metric">
                            <b-form-select v-model="rubricStatistic"
                                           :options="rubricStatOptions"/>
                        </b-input-group>

                        <b-input-group prepend="Relative"
                                       v-if="showRubricRelative">
                            <div class="form-control pl-2">
                                <b-form-checkbox v-model="rubricRelative"
                                                 :id="`rubric-relative-${id}`"
                                                 class="d-inline-block cursor-pointer" />

                                <label :for="`rubric-relative-${id}`"
                                       class="cursor-pointer">
                                    Relative to extreme score in category
                                </label>
                            </div>
                        </b-input-group>
                    </b-card>
                </div>

                <template v-for="row in rubric.rows"
                          v-if="rubricCatScatter[row.id]">
                    <div class="col-12 col-lg-6">
                        <b-card :header="`${row.header}: Correlation of item score with total score`">
                            <scatter-plot :chart-data="rubricCatScatter[row.id]"
                                          :options="rubricCatScatterOpts"
                                          :width="300"
                                          :height="200"/>
                        </b-card>
                    </div>
                </template>
            </template>
        </template>
    </template>
</div>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';
import * as stat from 'simple-statistics';

import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/reply';

import { WorkspaceFilter } from '@/models';
import { BarChart, ScatterPlot } from '@/components/Charts';
import Loader from '@/components/Loader';
import DatetimePicker from '@/components/DatetimePicker';
import DescriptionPopover from '@/components/DescriptionPopover';

export default {
    name: 'analytics-dashboard',

    props: {
        assignmentId: {
            type: Number,
            required: true,
        },
    },

    data() {
        return {
            id: this.$utils.getUniqueId(),
            loading: true,
            error: null,
            baseWorkspace: null,
            rubricStatistic: 'mean',
            rubricRelative: true,
            filters: [WorkspaceFilter.emptyFilter],
        };
    },

    computed: {
        ...mapGetters('courses', ['assignments']),
        ...mapGetters('rubrics', { allRubricResults: 'results' }),

        assignment() {
            return this.assignments[this.assignmentId];
        },

        assignmentCreated() {
            return this.assignment.getFormattedCreatedAt();
        },

        assignmentDeadline() {
            return this.assignment.getFormattedDeadline();
        },

        workspaceIds() {
            return this.$utils.getProps(this.assignment, null, 'analytics_workspace_ids');
        },

        currentWorkspaceId() {
            return this.$utils.getProps(this.workspaceIds, null, 0);
        },

        rubric() {
            return this.$utils.getProps(this.assignment, null, 'rubric');
        },

        filterResults() {
            return this.baseWorkspace.filter(this.filters);
        },

        baseSubmissionData() {
            return this.baseWorkspace.submissions;
        },

        latestSubmissions() {
            return this.baseWorkspace.filter([
                new WorkspaceFilter({ onlyLatestSubs: true }),
            ])[0];
        },

        latestSubmissionData() {
            return this.latestSubmissions.submissions;
        },

        latestInlineFeedbackSource() {
            return this.latestSubmissions.getSource('inline_feedback');
        },

        submissionSources() {
            return this.filterResults.map(r => r.submissions);
        },

        hasRubricSource() {
            return this.baseWorkspace.hasSource('rubric_data');
        },

        rubricSources() {
            if (!this.hasRubricSource) {
                return [];
            }
            return this.filterResults.map(r => r.getSource('rubric_data'));
        },

        hasManyRubricRows() {
            return this.$utils.getProps(this.rubricSource, 0, 'rowIds', 'length') > 8;
        },

        submissionDateHistogram() {
            // TODO: gray out dates outside of the filtered range.
            const base = this.baseSubmissionData.binSubmissionsByDate();
            const latest = this.latestSubmissionData.binSubmissionsByDate();
            const allDates = [...new Set([...Object.keys(base), ...Object.keys(latest)])].sort();

            const datasets = [
                {
                    label: 'All submissions',
                    data: allDates.map(d => base[d].length),
                },
                {
                    label: 'Latest submissions',
                    data: allDates.map(d => latest[d].length),
                },
            ];

            return { labels: allDates, datasets };
        },

        largeGradeHistogram() {
            return (
                this.$root.$isLargeWindow &&
                this.filters.length > 1 &&
                (!this.hasRubricSource || this.hasManyRubricRows)
            );
        },

        gradeHistogram() {
            let maxGrade = this.assignment.max_grade;
            if (maxGrade == null) {
                maxGrade = 10;
            }

            const bins = this.$utils.range(Math.ceil(maxGrade));
            const labels = bins.map(start => `${10 * start}% - ${10 * (start + 1)}%`);

            const datasets = this.submissionSources.map((source, i) => {
                const data = source.binSubmissionsByGrade();

                // We can't use source.submissionCount here, because some submissions
                // may have been filtered out, e.g. submissions without a grade.
                // TODO: Should we make a separate bin for ungraded subs?
                const nSubs = stat.sum(bins.map(bin => data[bin].length));

                return {
                    label: `Filter ${i}`,
                    data: bins.map(bin => 100 * data[bin].length / nSubs),
                };
            });

            return { labels, datasets };
        },

        gradeHistOpts() {
            return {
                scales: {
                    yAxes: [
                        {
                            ticks: {
                                beginAtZero: true,
                                stepSize: 1,
                            },
                            scaleLabel: {
                                display: true,
                                labelString: 'Percentage of students',
                            },
                        },
                    ],
                },
            };
        },

        rubricStatOptions() {
            return [
                'mean',
                'median',
                'mode',
                'rit',
                'rir',
            ];
        },

        showRubricRelative() {
            return ['mean', 'median', 'mode'].indexOf(this.rubricStatistic) !== -1;
        },

        rubricNormalizeFactors() {
            if (!this.showRubricRelative || !this.rubricRelative) {
                return null;
            }
            return this.rubric.rows.map(row => [row.minPoints, row.maxPoints]);
        },

        rubricMeanHistogram() {
            const datasets = this.rubricSources.map((source, i) => {
                let data = [];
                const stats = [];

                this.rubric.rows.forEach(row => {
                    const rowStats = {
                        mean: source.meanPerCat[row.id],
                        mode: source.modePerCat[row.id],
                        median: source.medianPerCat[row.id],
                        rit: source.ritPerCat[row.id],
                        rir: source.rirPerCat[row.id],
                        nTimesFilled: source.nTimesFilledPerCat[row.id],
                        rowId: row.id,
                    };
                    stats.push(rowStats);
                    data.push(rowStats[this.rubricStatistic]);

                    if (this.rubricNormalizeFactors != null) {
                        data = this.normalize(data);
                    }
                });

                return {
                    label: `Filter ${i}`,
                    data,
                    stats,
                };
            });

            return {
                labels: this.rubric.rows.map(row => row.header),
                datasets,
            };
        },

        rubricMeanHistOpts() {
            const getStats = (tooltipItem, data) => {
                const dataset = data.datasets[tooltipItem.datasetIndex];
                return dataset.stats[tooltipItem.index];
            };

            const label = (tooltipItem, data) => {
                const stats = getStats(tooltipItem, data);
                return this.rirMessage(stats.rir);
            };

            const afterLabel = (tooltipItem, data) => {
                const stats = getStats(tooltipItem, data);
                // Do not escape, chart.js does its own escaping.
                return [
                    `Times filled: ${stats.nTimesFilled}`,
                    `Mean: ${this.to2Dec(stats.mean)}`,
                    `Median: ${this.to2Dec(stats.median)}`,
                    `Mode: ${this.modeToString(stats.mode)}`,
                    `Rit: ${this.to2Dec(stats.rit) || '-'}`,
                    `Rir: ${this.to2Dec(stats.rir) || '-'}`,
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
            return this.rubric.rows.reduce(
                (acc, row) => {
                    const datasets = [].concat(...this.rubricSources.map((source, i) => {
                        const { ritItemsPerCat, rirItemsPerCat } = source;
                        const ritItems = ritItemsPerCat[row.id];
                        const rirItems = rirItemsPerCat[row.id];

                        if (ritItems.length === 0 && rirItems.length === 0) {
                            return [];
                        }

                        return [
                            {
                                label: `Total (Filter ${i})`,
                                data: ritItems.map(([x, y]) => ({ x, y })),
                            },
                            {
                                label: `Total - Item (Filter ${i})`,
                                data: rirItems.map(([x, y]) => ({ x, y })),
                            },
                        ];
                    }));

                    acc[row.id] = { datasets };
                    return acc;
                },
                {},
            );
        },

        rubricCatScatterOpts() {
            return {
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
                                labelString: 'Total score',
                            },
                        },
                    ],
                },
            };
        },
    },

    methods: {
        ...mapActions('analytics', ['loadWorkspace', 'clearAssignmentWorkspaces']),

        loadWorkspaceData() {
            this.loading = true;
            this.baseWorkspace = null;
            return this.loadWorkspace({
                workspaceId: this.currentWorkspaceId,
            }).then(
                res => {
                    const ws = res.data;
                    if (ws.id === this.currentWorkspaceId) {
                        this.baseWorkspace = ws;
                        this.error = null;
                        this.loading = false;
                    }
                    return res;
                },
                err => {
                    this.loading = false;
                    this.error = err;
                    throw err;
                },
            );
        },

        reloadWorkspace() {
            this.clearAssignmentWorkspaces().then(this.loadWorkspaceData);
        },

        updateFilter(idx, key, value) {
            const filter = this.filters[idx].update(key, value);
            this.$set(this.filters, idx, filter);
        },

        addFilter() {
            this.filters = [...this.filters, WorkspaceFilter.emptyFilter];
        },

        to2Dec(x) {
            return this.$utils.toMaxNDecimals(x, 2);
        },

        modeToString(mode) {
            // The mode is usually a number, but it can also be a list when multiple
            // values were the most common.
            if (Array.isArray(mode)) {
                return mode.map(this.to2Dec).join(', ');
            } else {
                return this.to2Dec(mode);
            }
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

    watch: {
        currentWorkspaceId: {
            immediate: true,
            handler() {
                this.loadWorkspaceData();
            },
        },

        filters() {
            this.$router.replace({
                query: {
                    ...this.$route.query,
                    'analytics-filters': JSON.stringify(this.filters),
                },
                hash: this.$route.hash,
            });
        },
    },

    mounted() {
        this.$root.$on('cg::submissions-page::reload', this.reloadWorkspace);
    },

    destroyed() {
        this.$root.$off('cg::submissions-page::reload', this.reloadWorkspace);
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

<style lang="less" scoped>
.card {
    margin-bottom: 1rem;

    .input-group:not(:last-child) {
        margin-bottom: 1rem;
    }
}

.metric {
    position: relative;
    text-align: center;

    label {
        padding: 0 1rem;
        margin-bottom: 0;
    }

    .description-popover {
        position: absolute;
        top: 0;
        right: 0.5rem;
    }
}
</style>
