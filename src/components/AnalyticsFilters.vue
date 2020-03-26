<template>
<b-card class="analytics-filters"
        header-class="d-flex">
    <template #header>
        <div class="flex-grow-1">
            Filters
        </div>

        <div class="d-flex flex-grow-0">
            <div class="icon-button danger"
                 @click="resetFilters()"
                 v-b-popover.hover.top="'Reset'">
                <icon name="reply" />
            </div>
        </div>
    </template>

    <div class="row">
        <div v-for="filter, i in filters"
             :key="i"
             class="col-6">
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

                        <div :id="`analytics-filter-split-${id}-${i}`"
                             class="icon-button"
                             v-b-popover.hover.top="'Split'">
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

                    <b-popover :target="`analytics-filter-split-${id}-${i}`"
                               triggers="click"
                               placement="leftbottom"
                               title="Split on">
                        <b-input-group class="mb-2 p-2 border rounded text-left">
                            <b-checkbox v-model="splitLatest">
                                Split on latest
                            </b-checkbox>
                        </b-input-group>

                        <b-input-group class="mb-2">
                            <input v-model="splitGrade"
                                   class="form-control"
                                   type="number"
                                   placeholder="Grade" />
                        </b-input-group>

                        <b-input-group class="mb-2">
                            <datetime-picker v-model="splitDate"
                                             placeholder="Date"/>
                        </b-input-group>

                        <submit-button class="float-right mb-2"
                                       variant="primary"
                                       :submit="() => splitFilter(i)"
                                       @after-success="afterSplitFilter">
                            <icon name="check" />
                        </submit-button>
                    </b-popover>
                </template>

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
                                      @click="updateFilter(i, 'submittedAfter', null)">
                                <icon name="reply" />
                            </b-button>
                        </template>
                </b-input-group>
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
import 'vue-awesome/icons/unlink';
import 'vue-awesome/icons/scissors';
import 'vue-awesome/icons/copy';

import { WorkspaceFilter } from '@/models';
import SubmitButton from '@/components/SubmitButton';
import DatetimePicker from '@/components/DatetimePicker';

export default {
    name: 'analytics-filters',

    props: {
        assignmentId: {
            type: Number,
            required: true,
        },
        filters: {
            validate(value) {
                return Array.isArray(value) && value.every(x => x instanceof WorkspaceFilter);
            },
            required: true,
        },
    },

    model: {
        prop: 'filters',
        event: 'change',
    },

    data() {
        return {
            id: this.$utils.getUniqueId(),
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

        assignmentCreated() {
            return this.assignment.getFormattedCreatedAt();
        },

        assignmentDeadline() {
            return this.assignment.getFormattedDeadline();
        },

        deleteDisabled() {
            return this.filters.length === 1;
        },
    },

    watch: {
        assignmentId: {
            immediate: true,
            handler() {
                this.resetFilters();
            },
        },
    },

    methods: {
        resetFilters() {
            this.$emit('change', [WorkspaceFilter.emptyFilter]);
        },

        resetSplitParams() {
            this.splitLatest = false;
            this.splitGrade = '';
            this.splitDate = '';
        },

        updateFilter(idx, key, value) {
            const filter = this.filters[idx].update(key, value);
            this.$set(this.filters, idx, filter);
        },

        addFilter() {
            this.$emit('change', [
                ...this.filters,
                WorkspaceFilter.emptyFilter,
            ]);
        },

        replaceFilter(idx, ...newFilters) {
            const fs = this.filters;
            this.$emit('change', [
                ...fs.slice(0, idx),
                ...newFilters,
                ...fs.slice(idx + 1),
            ]);
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
            const result = this.filters[idx].split({
                latest: this.splitLatest,
                grade: this.splitGrade,
                date: this.splitDate,
            });
            this.replaceFilter(idx, ...result);
        },

        afterSplitFilter() {
            this.$afterRerender(() => {
                this.$root.$emit('bv::hide::popover');
                this.resetSplitParams();
            });
        },

        formatDate(d) {
            return d == null ? null : this.$utils.readableFormatDate(d);
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
    },
};
</script>

<style lang="less" scoped>
</style>
