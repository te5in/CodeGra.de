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

            <div :id="shareBtnId"
                 class="icon-button"
                 tabindex="-1"
                 style="outline: none !important;"
                 v-b-popover.hover.top="'Share current filters'">
                <icon name="share-alt" />

                <b-popover :target="shareBtnId"
                           triggers="click blur"
                           placement="bottom"
                           title="Share filters">
                    <p class="mb-2 text-justify">
                        <small>
                            Anyone with this URL and permissions to view this
                            assignment's analytics dashboard will get the
                            current view.
                        </small>
                    </p>

                    <b-input-group class="flex-row" style="flex-wrap: nowrap;">
                        <div class="form-control text-truncate">
                            <small>
                                {{ currentUrl }}
                            </small>
                        </div>

                        <template #append>
                            <b-button @click="copyUrlToClipboard">
                                <icon name="clipboard" />
                            </b-button>
                        </template>
                    </b-input-group>
                </b-popover>
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
                                deleteDisabled ?  'You cannot delete the only filter' : 'Delete'
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
                                             :placeholder="`${assignmentCreated} (Assignment created)`"
                                             :config="submittedDateTimeConfig"/>

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
                                             :placeholder="`${assignmentDeadline} (Assignment deadline)`"
                                             :config="submittedDateTimeConfig"/>

                            <template #append>
                                <b-button variant="warning"
                                          :disabled="filter.submittedBefore == null"
                                          @click="updateFilter(i, 'submittedBefore', null)">
                                    <icon name="reply" />
                                </b-button>
                            </template>
                        </b-input-group>

                        <!-- Must have a z-index otherwise the reset buttons of the
                             other options  are visible over the multiselect popup -->
                        <b-input-group class="grader-group">
                            <multiselect
                                class="d-flex"
                                :max-height="150"
                                :value="filter.assignees"
                                @input="updateFilter(i, 'assignees', $event)"
                                :options="assignees"
                                multiple
                                searchable
                                open-direction="top"
                                track-by="id"
                                label="name"
                                :close-on-select="false"
                                placeholder="Select graders"
                                internal-search>
                                <span slot="noResult">
                                    No graders with this name.
                                </span>
                            </multiselect>

                            <template #append>
                                <b-button variant="warning"
                                          :disabled="filter.assignees.length === 0"
                                          @click="updateFilter(i, 'assignees', [])">
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
                                   :min="0"
                                   :max="assignmentMaxGrade"
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
                                             placeholder="Date"
                                             :config="{
                                                 minDate: nthFirstSubmissionDate(i).toISOString(),
                                                 maxDate: nthLastSubmissionDate(i).toISOString(),
                                             }"/>
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

    <div ref="copyContainer" />
</b-card>
</template>

<script>
import { mapGetters } from 'vuex';

import Multiselect from 'vue-multiselect';

import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/reply';
import 'vue-awesome/icons/plus';
import 'vue-awesome/icons/unlink';
import 'vue-awesome/icons/scissors';
import 'vue-awesome/icons/copy';
import 'vue-awesome/icons/share-alt';
import 'vue-awesome/icons/clipboard';

import { Workspace, WorkspaceFilter } from '@/models/analytics';
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
        initialData: {
            type: Array,
            default: null,
        },
    },

    data() {
        const id = this.$utils.getUniqueId();

        return {
            filters: this.defaultFilters(this.initialData),
            isSplitting: null,
            splitLatest: false,
            splitGrade: '',
            splitDate: '',

            shareBtnId: `analytics-filters-share-btn-${id}`,
        };
    },

    computed: {
        ...mapGetters('courses', ['assignments']),
        ...mapGetters('users', ['getUser']),

        currentUrl() {
            // We can't get an actual URL from a $route, but we want this to
            // be updated whenever $route changes.
            // eslint-disable-next-line
            const route = this.$route;
            return window.location.href;
        },

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

        submittedDateTimeConfig() {
            return {
                minDate: this.workspace.submissions.firstSubmissionDate.toISOString(),
                maxDate: this.workspace.submissions.lastSubmissionDate.toISOString(),
                defaultHour: 23,
                defaultMinute: 59,
            };
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

        assignees() {
            const ids = this.workspace.submissions.assigneeIds;
            return [...ids].map(id => this.getUser(id));
        },

        assigneeOptions() {
            return this.assignees.map(user => ({
                text: user.name,
                value: user,
            }));
        },
    },

    methods: {
        defaultFilters(filters) {
            if (filters == null || filters.length === 0) {
                return [WorkspaceFilter.emptyFilter];
            } else {
                return filters.map(f => new WorkspaceFilter(f));
            }
        },

        resetFilters() {
            this.filters = this.defaultFilters();
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
            this.filters = [WorkspaceFilter.emptyFilter, ...this.filters];
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
            this.filters = [...fs.slice(0, idx), ...newFilters, ...fs.slice(idx + 1)];
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

        isSplittingOther(idx) {
            return this.isSplitting != null && this.isSplitting !== idx;
        },

        nthFirstSubmissionDate(idx) {
            return this.results[idx].submissions.firstSubmissionDate;
        },

        nthLastSubmissionDate(idx) {
            return this.results[idx].submissions.lastSubmissionDate;
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

        copyUrlToClipboard(event) {
            const url = window.location.href;
            this.$copyText(url, this.$refs.copyContainer);
            event.target.blur();
        },
    },

    watch: {
        workspace() {
            this.resetFilters();
        },

        filters: {
            immediate: true,
            handler() {
                this.isSplitting = null;
                this.$emit('serialize', this.filters.map(f => {
                    const filter = Object.assign({}, f);
                    if (filter.submittedAfter != null) {
                        filter.submittedAfter = filter.submittedAfter.toISOString();
                    }
                    if (filter.submittedBefore != null) {
                        filter.submittedAfter = filter.submittedAfter.toISOString();
                    }
                    return filter;
                }));
            },
        },

        results: {
            immediate: true,
            handler() {
                this.$emit('results', this.results);
            },
        },
    },

    components: {
        Icon,
        Multiselect,
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

<style lang="less">
.analytics-filters {
    .grader-group {
        display: flex;
        flex-wrap: nowrap;
        z-index: 10;
    }

    .multiselect {
        flex: 1 1 auto;
        width: auto;

        .multiselect__tags {
            width: 100%;
            border-top-right-radius: 0;
            border-bottom-right-radius: 0;
        }
    }
}
</style>
