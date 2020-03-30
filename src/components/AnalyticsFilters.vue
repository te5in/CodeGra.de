<template>
<b-card class="analytics-filters"
        header-class="d-flex">
    <template #header>
        <div class="flex-grow-1">
            Filters
        </div>

        <div class="d-flex flex-grow-0">
            <div class="icon-button"
                 @click="addFilter()"
                 v-b-popover.hover.top="'Add filter'">
                <icon name="plus" />
            </div>

            <div class="icon-button danger"
                 @click="resetFilters()"
                 v-b-popover.hover.top="'Clear all'">
                <icon name="reply" />
            </div>
        </div>
    </template>

    <div class="row">
        <div v-for="filter, i in filters"
             :key="i"
             class="col-12 col-xl-6">
            <b-card header-class="d-flex">
                <template #header>
                    <div class="flex-grow-1">
                        {{ filter.toString() }}
                    </div>

                    <div class="d-flex flex-grow-0">
                        <div class="icon-button"
                             @click="duplicateFilter(i)"
                             v-b-popover.hover.top="'Duplicate'">
                            <icon name="copy" />
                        </div>

                        <div class="icon-button"
                             :class="{
                                 active: isSplitting === i,
                                 'text-muted': isSplittingOther(i),
                             }"
                             @click="toggleSplitFilter(i)"
                             v-b-popover.hover.top="
                                isSplittingOther(i) ? 'Already splitting another filter' : 'Split'
                            ">
                            <icon name="scissors" />
                        </div>

                        <div class="icon-button danger"
                             :class="{ 'text-muted': deleteDisabled }"
                             @click="deleteFilter(i)"
                             v-b-popover.hover.top="
                                deleteDisabled ?  'You cannot delete the last filter' : 'Delete'
                             ">
                            <icon name="times" />
                        </div>
                    </div>
                </template>

                <div class="controls">
                    <div class="filter-controls"
                        :class="{ active: isSplitting !== i }">
                        <b-input-group prepend="Latest">
                            <div class="form-control pl-2">
                                <b-form-checkbox :checked="filter.onlyLatestSubs"
                                                 @input="updateFilter(i, 'onlyLatestSubs', $event)"
                                                 class="d-inline-block">
                                    Only use latest submissions
                                </b-form-checkbox>
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
                                :placeholder="assignmentMaxGrade"
                                :min="filter.minGrade"
                                :max="assignmentMaxGrade"
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
                            <datetime-picker :value="formatDate(filter.submittedAfter)"
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
                            <datetime-picker :value="formatDate(filter.submittedBefore)"
                                            @input="updateFilter(i, 'submittedBefore', $event)"
                                            :placeholder="`${assignmentDeadline} (Assignment deadline)`"/>

                                <template #append>
                                    <b-button variant="warning"
                                            :disabled="filter.submittedBefore == null"
                                            @click="updateFilter(i, 'submittedBefore', null)">
                                        <icon name="reply" />
                                    </b-button>
                                </template>
                        </b-input-group>

                        <analytics-general-stats
                            :base-workspace="results[i]"
                            class="mb-0" />
                    </div>

                    <div class="split-controls"
                        :class="{ active: isSplitting === i }">
                        <b-input-group>
                            <b-input-group-prepend is-text>
                                Latest

                                <description-popover hug-text placement="top">
                                    TODO Split on latest...
                                </description-popover>
                            </b-input-group-prepend>

                            <b-form-checkbox v-model="splitLatest"
                                            class="form-control"
                                            style="padding-left: 2.25rem;">
                                Split on latest
                            </b-form-checkbox>
                        </b-input-group>

                        <b-input-group>
                            <b-input-group-prepend is-text>
                                Grade

                                <description-popover hug-text placement="top">
                                    TODO Split on the grade...
                                </description-popover>
                            </b-input-group-prepend>

                            <input v-model="splitGrade"
                                class="form-control placeholder-left"
                                type="number"
                                :placeholder="`Avg. of filter = ${filterAvgGrade(filter)}`" />
                        </b-input-group>

                        <b-input-group>
                            <b-input-group-prepend is-text>
                                Submitted

                                <description-popover hug-text placement="top">
                                    TODO Split on submitted...
                                </description-popover>
                            </b-input-group-prepend>

                            <datetime-picker v-model="splitDate"
                                            placeholder="Date" />
                        </b-input-group>

                        <div v-for="split in splitResults">
                            <small class="pl-1 text-muted">
                                {{ split.filter.toString() }}
                            </small>
                            <analytics-general-stats
                                :base-workspace="split"
                                class="mb-0" />
                        </div>

                        <div class="mt-3">
                            <submit-button class="float-right"
                                        variant="primary"
                                        :submit="() => splitFilter(i)"
                                        @after-success="afterSplitFilter">
                                <icon name="check" />
                            </submit-button>
                        </div>
                    </div>
                </div>
            </b-card>
        </div>
    </div>

    <b-button variant="primary"
              class="float-right"
              @click="addFilter">
        Add filter
    </b-button>
</b-card>
</template>

<script>
import { mapGetters } from 'vuex';

import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/reply';
import 'vue-awesome/icons/plus';
import 'vue-awesome/icons/unlink';
import 'vue-awesome/icons/scissors';
import 'vue-awesome/icons/copy';

import { Workspace, WorkspaceFilter } from '@/models';
import SubmitButton from '@/components/SubmitButton';
import DatetimePicker from '@/components/DatetimePicker';
import DescriptionPopover from '@/components/DescriptionPopover';
import AnalyticsGeneralStats from '@/components/AnalyticsGeneralStats';

export default {
    name: 'analytics-filters',

    props: {
        assignmentId: {
            type: Number,
            required: true,
        },
        workspace: {
            type: Workspace,
            required: true,
        },
    },

    data() {
        return {
            filters: [WorkspaceFilter.emptyFilter],
            isSplitting: null,
            splitLatest: false,
            splitGrade: '',
            splitDate: '',
        };
    },

    computed: {
        ...mapGetters('courses', ['assignments']),

        assignment() {
            return this.assignments[this.assignmentId];
        },

        assignmentMaxGrade() {
            return this.assignment.maxGrade || 10;
        },

        assignmentCreated() {
            return this.assignment.getFormattedCreatedAt();
        },

        assignmentDeadline() {
            return this.assignment.getFormattedDeadline();
        },

        results() {
            return this.workspace.filter(this.filters);
        },

        deleteDisabled() {
            return this.filters.length === 1;
        },

        splitFilters() {
            // The new filters produced by the current split.
            if (this.isSplitting == null) {
                return [];
            }

            return this.filters[this.isSplitting].split({
                latest: this.splitLatest,
                grade: this.splitGrade,
                date: this.splitDate,
            });
        },

        splitResults() {
            return this.workspace.filter(this.splitFilters);
        },
    },

    watch: {
        workspace: {
            immediate: true,
            handler() {
                this.resetFilters();
            },
        },

        filters: {
            immediate: true,
            handler() {
                this.isSplitting = null;
                this.$router.replace({
                    query: {
                        ...this.$route.query,
                        'analytics-filters': JSON.stringify(this.filters),
                    },
                    hash: this.$route.hash,
                });
            },
        },

        results: {
            immediate: true,
            handler() {
                this.$emit('results', this.results);
            },
        },
    },

    methods: {
        resetFilters() {
            this.filters = [WorkspaceFilter.emptyFilter];
            this.resetSplitParams();
        },

        resetSplitParams() {
            this.isSplitting = null;
            this.splitLatest = false;
            this.splitGrade = '';
            this.splitDate = '';
        },

        updateFilter(idx, key, value) {
            const filter = this.filters[idx].update(key, value);
            this.$set(this.filters, idx, filter);
        },

        addFilter() {
            this.filters = [...this.filters, WorkspaceFilter.emptyFilter];
        },

        toggleSplitFilter(idx) {
            if (this.isSplitting == null) {
                this.isSplitting = idx;
            } else if (this.isSplitting === idx) {
                this.resetSplitParams();
            }
        },

        replaceFilter(idx, ...newFilters) {
            const fs = this.filters;
            this.filters = [
                ...fs.slice(0, idx),
                ...newFilters,
                ...fs.slice(idx + 1),
            ];
        },

        deleteFilter(idx) {
            if (!this.deleteDisabled) {
                this.replaceFilter(idx);
            }
        },

        duplicateFilter(idx) {
            // Replace the filter with two copies of itself.
            const f = this.filters[idx];
            this.replaceFilter(idx, f, f);
        },

        async splitFilter(idx) {
            // Replace the filter with the result of splitting it.
            this.replaceFilter(idx, ...this.splitFilters);
        },

        afterSplitFilter() {
            this.$afterRerender(() => {
                this.$root.$emit('bv::hide::popover');
                this.resetSplitParams();
            });
        },

        isSplittingOther(i) {
            return this.isSplitting != null && this.isSplitting !== i;
        },

        filterAvgGrade(filter) {
            let { minGrade, maxGrade } = filter;
            if (minGrade == null) {
                minGrade = 0;
            }
            if (maxGrade == null) {
                const assigMax = this.assignment.maxGrade;
                maxGrade = assigMax == null ? 10 : assigMax;
            }
            return (minGrade + maxGrade) / 2;
        },

        formatDate(d) {
            return d == null ? null : this.$utils.readableFormatDate(d);
        },

        to2Dec(x) {
            return this.$utils.toMaxNDecimals(x, 2);
        },
    },

    mounted() {
    },

    destroyed() {
    },

    components: {
        Icon,
        SubmitButton,
        DatetimePicker,
        DescriptionPopover,
        AnalyticsGeneralStats,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.controls {
    overflow: hidden;
    display: flex;
    flex-direction: row;
    flex-wrap: nowrap;
}

.filter-controls,
.split-controls {
    flex: 0 0 100%;
    margin-right: 1rem;
}

.filter-controls {
    margin-left: calc(-100% - 1rem);
    transition: margin-left @transition-duration;

    &.active {
        margin-left: 0;
    }
}
</style>
