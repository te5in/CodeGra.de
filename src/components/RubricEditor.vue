<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<loader class="rubric-editor" v-if="loading"/>
<div v-else class="rubric-editor" :class="{ editable }">
    <b-tabs no-fade
            v-model="currentCategory">
        <b-nav-item slot="tabs"
                    @click.prevent="appendRow"
                    href="#"
                    v-if="editable">
            +
        </b-nav-item>


        <b-tab class="rubric"
               v-for="(rubric, i) in rubrics"
               :title="rubricCategoryTitle(rubric)"
               :key="`rubric-${rubric.id}-${i}`">

            <b-card @mouseenter="$set(lockPopoverShown, rubric.id, true)"
                    @mouseleave="$delete(lockPopoverShown, rubric.id)">
                <div class="card-header rubric-header">
                    <b-input-group v-if="editable" class="mb-3">
                        <b-input-group-prepend is-text>
                            Category name
                        </b-input-group-prepend>

                        <input class="form-control"
                               placeholder="Category name"
                               @keydown.ctrl.enter="clickSubmit"
                               v-model="rubric.header"/>

                        <b-input-group-append is-text
                                              v-if="rubric.locked"
                                              v-b-popover.hover.top="rowData[rubric.id].content">
                            <icon name="lock" />
                        </b-input-group-append>

                        <b-input-group-append v-else>
                            <submit-button variant="danger"
                                           label="Remove category"
                                           :wait-at-least="0"
                                           :submit="() => deleteRow(i)"
                                           @after-success="afterDeleteRow"
                                           confirm="Do you really want to delete this category?" />
                        </b-input-group-append>
                    </b-input-group>

                    <textarea class="form-control"
                              placeholder="Category description"
                              :tabindex="currentCategory === i ? null: -1"
                              v-model="rubric.description"
                              @keydown.ctrl.enter.prevent="clickSubmit"
                              v-if="editable"/>
                    <p class="mb-0" v-else>
                        {{ rubric.description }}

                        <template v-if="rubric.locked">
                            <b-popover :show="lockPopoverShown[rubric.id]"
                                       :target="`rubric-lock-${rowData[rubric.id].id}`"
                                       :content="rowData[rubric.id].content"
                                       triggers=""
                                       placement="top" />

                            <icon name="lock"
                                  class="float-right"
                                  :id="`rubric-lock-${rowData[rubric.id].id}`" />
                        </template>
                    </p>
                </div>
                <b-card-group class="rubric-items-container">
                    <b-card class="rubric-item"
                            v-for="(item, j) in rubric.items"
                            :key="`rubric-item-${item.id}-${j}-${i}`">
                        <b-input-group class="item-header-row">
                            <input v-if="editable"
                                   type="number"
                                   class="form-control item-points"
                                   step="any"
                                   :tabindex="currentCategory === i ? null: -1"
                                   placeholder="Points"
                                   @change="item.points = parseFloat(item.points)"
                                   @keydown="addItem(i, j)"
                                   @keydown.ctrl.enter="clickSubmit"
                                   v-model="item.points"/>
                            <span v-else
                                  class="item-points input disabled">
                                {{ item.points }}
                            </span>
                            <input type="text"
                                   v-if="editable"
                                   class="form-control item-header"
                                   placeholder="Header"
                                   :tabindex="currentCategory === i ? null: -1"
                                   @keydown="addItem(i, j)"
                                   @keydown.ctrl.enter="clickSubmit"
                                   v-model="item.header"/>
                            <span v-else class="input item-header disabled">
                                {{ item.header }}
                            </span>
                            <div class="item-info-button"
                                 v-if="rubric.items.length - 1 === j && rowData[rubric.id].editable"
                                 v-b-popover.top.hover="'Simply start typing to add a new item.'">
                                <icon name="info"/>
                            </div>
                            <div class="item-delete-button"
                                 v-else-if="rowData[rubric.id].editable"
                                 @click="deleteItem(i, j)">
                                <icon name="times"/>
                            </div>
                        </b-input-group>
                        <textarea v-model="item.description"
                                  class="item-description form-control"
                                  v-if="editable"
                                  :rows="8"
                                  :tabindex="currentCategory === i ? null: -1"
                                  @keydown="addItem(i, j)"
                                  @keydown.ctrl.enter.prevent="clickSubmit"
                                  placeholder="Description"/>
                        <p v-else
                           class="form-control input item-description disabled">
                            {{ item.description }}
                        </p>
                    </b-card>
                </b-card-group>
            </b-card>
        </b-tab>

        <div slot="empty" class="text-center text-muted empty" v-if="editable">
            <p>This assignment does not have rubric yet. Click the '+' to add a category.</p>
            <hr>

            <p>You can also import a rubric from a different assignment:</p>
            <b-alert v-if="loadAssignmentsFailed"
                     variant="danger"
                     class="assignment-alert"
                     show>
                Loading assignments failed.
            </b-alert>
            <b-input-group v-else>
                <multiselect
                    class="assignment-selector"
                    v-model="importAssignment"
                    :options="assignments || []"
                    :searchable="true"
                    :custom-label="a => `${a.course.name} - ${a.name}`"
                    :multiple="false"
                    track-by="id"
                    label="label"
                    :close-on-select="true"
                    :hide-selected="false"
                    placeholder="Select old assignment"
                    :internal-search="true"
                    :loading="loadingAssignments">
                    <span slot="noResult">
                        No results were found.
                    </span>
                </multiselect>
                <template slot="append">
                    <submit-button ref="importBtn"
                                   :disabled="!importAssignment"
                                   :submit="loadOldRubric"
                                   @after-success="afterLoadOldRubric"/>
                </template>
            </b-input-group>
        </div>

        <b-card class="extra-bar" v-if="!editable">
            <span>
                To get a full mark you need to score
                {{ internalFixedMaxPoints || curMaxPoints }} points in this
                rubric.
            </span>
            <slot/>
        </b-card>
    </b-tabs>

    <b-modal id="modal_delete_rubric" title="Are you sure?" :hide-footer="true">
        <p style="text-align: center;">
            By deleting a rubric the rubric and all grades given with it will be
            lost forever! So are you really sure?
        </p>
        <b-button-toolbar justify>
            <submit-button label="Yes"
                           variant="outline-danger"
                           :submit="deleteRubric"
                           :filter-error="deleteFilter"
                           @after-success="afterDeleteRubric"/>
            <b-btn class="text-center"
                   variant="success"
                   @click="$root.$emit('bv::hide::modal', 'modal_delete_rubric')">
                No!
            </b-btn>
        </b-button-toolbar>
    </b-modal>

    <div class="button-bar justify-content-center" v-if="editable">
        <b-alert v-if="showMaxPointsWarning"
                 variant="warning"
                 show>
            {{ maximumPointsWarningText }}
        </b-alert>
        <div class="override-checkbox">
            <b-input-group class="max-points-input-group">
                <b-input-group-prepend is-text>
                    Points needed for a 10:
                </b-input-group-prepend>
                <input type="number"
                       min="0"
                       step="1"
                       v-model="internalFixedMaxPoints"
                       class="form-control"
                       :placeholder="curMaxPoints"/>
                <b-input-group-append is-text>
                    out of {{ curMaxPoints }}
                    <description-popover
                        placement="top"
                        hug-text
                        description="The maximum amount of points a user can get
                                     for this rubric. You can set this to a
                                     higher or lower value manually, by default
                                     it is the sum of the max value in each
                                     category."/>
                </b-input-group-append>
            </b-input-group>
        </div>
    </div>

    <hr v-if="editable"/>

    <b-card class="button-bar" v-if="editable">
        <b-button-group class="danger-buttons">
            <b-button variant="danger"
                      v-b-popover.top.hover="'Delete rubric'"
                      @click="showDeleteModal"
                      :disabled="rubrics.length === 0">
                <icon name="times"/>
            </b-button>

            <submit-button variant="danger"
                           v-b-popover.top.hover="'Reset rubric'"
                           :submit="resetRubric"
                           confirm="Are you sure you want to revert your changes?"
                           :disabled="rubrics.length === 0">
                <icon name="reply"/>
            </submit-button>
        </b-button-group>

        <submit-button ref="submitButton"
                       :confirm="deletedRubricItems.length > 0 ? 'yes' : ''"
                       :submit="submit"
                       @after-success="afterSubmit">
            <div slot="confirm" style="text-align: justify;">
                <p>
                Are you sure you want to remove the following item{{ deletedRubricItems.length > 1 ? 's' : ''}}?
                </p>

                <b>Deleted item{{ deletedRubricItems.length > 1 ? 's' : ''}}</b>
                <ul>
                    <li v-for="item in deletedRubricItems">{{ item }}</li>
                </ul>
            </div>

            <div slot="error"
                 slot-scope="scope"
                 class="error-popover text-left">
                <p v-if="scope.error.empty" class="mb-2">
                    You cannot submit an empty rubric.
                </p>

                <p v-if="scope.error.unnamed" class="mb-2">
                    There are unnamed categories!
                </p>

                <p v-if="scope.error.categories.length > 0" class="mb-2">
                    The following categor{{ scope.error.categories.length >= 2 ? 'ies have' : 'y has' }}
                    no items.

                    <ul>
                        <li v-for="msg in scope.error.categories">
                            {{ msg }}
                        </li>
                    </ul>
                </p>

                <p v-if="scope.error.items.length > 0" class="mb-2">
                    Make sure "points" is a number for the following
                    item{{ scope.error.items.length >= 2 ? 's' : '' }}:

                    <ul>
                        <li v-for="msg in scope.error.items">
                            {{ msg }}
                        </li>
                    </ul>
                </p>
            </div>
        </submit-button>
    </b-card>
</div>
</template>

<script>
import Multiselect from 'vue-multiselect';
import { mapActions, mapGetters, mapMutations } from 'vuex';

import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/plus';
import 'vue-awesome/icons/times';
import 'vue-awesome/icons/info';
import 'vue-awesome/icons/lock';
import 'vue-awesome/icons/reply';

import { formatGrade } from '@/utils';

import SubmitButton from './SubmitButton';
import Loader from './Loader';
import DescriptionPopover from './DescriptionPopover';

export default {
    name: 'rubric-editor',
    data() {
        return {
            id: this.$utils.getUniqueId(),
            rubrics: [],
            selected: null,
            loading: true,
            currentCategory: 0,
            assignmentId: this.assignment.id,
            internalFixedMaxPoints: this.assignment.fixed_max_rubric_points,
            assignments: null,
            importAssignment: null,
            loadingAssignments: false,
            loadAssignmentsFailed: false,
            lockPopoverShown: {},
            oldItemIds: {},
        };
    },

    props: {
        assignment: {
            default: null,
        },
        editable: {
            type: Boolean,
            default: true,
        },
        fixedMaxPoints: {
            type: Number,
            default: null,
        },
        defaultRubric: {
            default: null,
        },
        hidden: {
            type: Boolean,
            default: false,
        },
    },

    watch: {
        assignmentId: {
            immediate: true,
            handler() {
                this.getAndSetRubrics();
                this.storeLoadAutoTest({
                    autoTestId: this.autoTestConfigId,
                });
            },
        },

        hidden() {
            this.maybeLoadOtherAssignments();
        },

        editable() {
            this.maybeLoadOtherAssignments();
        },
    },

    async mounted() {
        if (this.defaultRubric) {
            this.setRubricData(this.defaultRubric);
            this.loading = false;
        } else {
            await this.getAndSetRubrics().then(() => {
                this.loading = false;
            });
        }
        this.maybeLoadOtherAssignments();

        // TODO: This should probably do something special when there are
        // changes to the current rubric.
        this.$root.$on('cg::rubric-editor::reload', this.resetRubric);
    },

    destroyed() {
        this.$root.$off('cg::rubric-editor::reload', this.resetRubric);
    },

    computed: {
        ...mapGetters('autotest', {
            allAutoTests: 'tests',
        }),

        deletedRubricItems() {
            const curItemIds = this.getRubricItemIds(this.rubrics);
            const removedIds = Object.keys(this.oldItemIds).filter(id => curItemIds[id] == null);
            return removedIds.map(id => this.oldItemIds[id]);
        },

        autoTestConfigId() {
            return this.assignment.auto_test_id;
        },

        autoTestConfig() {
            return this.allAutoTests[this.autoTestConfigId];
        },

        maximumPointsWarningText() {
            const num = Number(this.internalFixedMaxPoints);
            if (num < this.curMaxPoints) {
                return `This means that a 10 will already be achieved with ${num} out of ${
                    this.curMaxPoints
                } rubric points.`;
            } else {
                return `This means that it will not be possible to achieve a 10, but a ${formatGrade(
                    this.curMaxPoints / num * 10,
                )} will be the maximum achievable grade.`;
            }
        },

        showMaxPointsWarning() {
            return (
                this.internalFixedMaxPoints !== '' &&
                this.internalFixedMaxPoints != null &&
                Number(this.internalFixedMaxPoints) !== this.curMaxPoints
            );
        },

        curMaxPoints() {
            return this.calcMaxPoints(this.rubrics);
        },

        rowData() {
            const { rubrics, editable, autoTestConfig } = this;

            if (rubrics == null) {
                return {};
            }

            const autoTestRun = autoTestConfig && autoTestConfig.runs[0];

            return rubrics.reduce((acc, row) => {
                acc[row.id] = {
                    id: `rubric-editor-${this.id}-row-${row.id}`,
                    content: this.lockPopover(row),
                    // The row is editable if the entire rubric is editable.
                    // However it is not editable if the row is locked, and
                    // the AutoTest has been started.
                    editable: editable && !(row.locked && autoTestRun != null),
                };
                return acc;
            }, {});
        },

        autoTestLockPopover() {
            let msg =
                'This is an AutoTest category. It will be filled once the ' +
                'AutoTest for this assignment is done running. ';

            switch (this.autoTestConfig && this.autoTestConfig.grade_calculation) {
                case 'full':
                    msg += 'You need to reach the upper bound of a rubric item to achieve it.';
                    break;
                case 'partial':
                    msg += 'You need to reach the lower bound of a rubric item to achieve it.';
                    break;
                default:
                    break;
            }

            return msg;
        },
    },

    methods: {
        ...mapActions('courses', ['forceLoadRubric', 'setRubric']),
        ...mapActions('submissions', ['forceLoadSubmissions']),

        ...mapActions('autotest', {
            storeLoadAutoTest: 'loadAutoTest',
        }),

        ...mapMutations('rubrics', {
            storeClearRubric: 'clearRubric',
        }),

        setOldRubricIds() {
            this.oldItemIds = this.getRubricItemIds(this.rubrics);
        },

        getRubricItemIds(rows) {
            return rows.reduce((accum, row) => {
                row.items.forEach(item => {
                    if (item.id != null) {
                        const itemHeader = item.header || '[No name]';
                        const rowHeader = row.header || '[No name]';
                        accum[item.id] = `${rowHeader} - ${itemHeader}`;
                    }
                });
                return accum;
            }, {});
        },

        maybeLoadOtherAssignments() {
            if (
                this.editable &&
                !this.hidden &&
                this.assignments === null &&
                this.rubrics.length === 0
            ) {
                this.loadAssignments();
            }
        },

        loadOldRubric() {
            return this.$http.post(`/api/v1/assignments/${this.assignmentId}/rubric`, {
                old_assignment_id: this.importAssignment.id,
            });
        },

        afterLoadOldRubric(response) {
            this.importAssignment = null;
            this.setRubricData(response.data);
            this.setRubric({
                assignmentId: this.assignmentId,
                rubric: response.data,
                maxPoints: this.calcMaxPoints(response.data),
            });
            this.forceLoadSubmissions(this.assignmentId);

            // TODO: Improve use of rubric store.
            // Clear rubric from the rubric store so it will be reloaded.
            this.storeClearRubric({ assignmentId: this.assignmentId });
        },

        loadAssignments() {
            this.loadingAssignments = true;
            this.assignments = [];
            this.$http.get('/api/v1/assignments/?only_with_rubric').then(
                ({ data }) => {
                    this.assignments = data;
                    this.loadingAssignments = false;
                },
                () => {
                    this.loadAssignmentsFailed = true;
                    this.loadingAssignments = false;
                },
            );
        },

        getEmptyItem() {
            return {
                points: '',
                header: '',
                description: '',
            };
        },

        resetFixedMaxPoints() {
            this.internalFixedMaxPoints = null;
            this.ensureFixedMaxPoints();

            return this.$http.put(`/api/v1/assignments/${this.assignmentId}/rubrics/`, {
                max_points: this.internalFixedMaxPoints,
            });
        },

        afterResetFixedMaxPoints(response) {
            this.setRubric({
                assignmentId: this.assignmentId,
                rubric: response.data,
                maxPoints: this.internalFixedMaxPoints,
            });
        },

        getEmptyRow() {
            return {
                header: '',
                description: '',
                items: [this.getEmptyItem()],
            };
        },

        resetRubric() {
            this.loading = true;
            return this.getAndSetRubrics().then(
                () => {
                    this.loading = false;
                },
                err => {
                    this.loading = false;
                    throw err;
                },
            );
        },

        async setRubricData(serverRubrics) {
            const editable = this.$utils.getProps(this, false, 'editable');

            if (this.autoTestConfigId != null && this.autoTestConfig == null) {
                await this.storeLoadAutoTest({
                    autoTestId: this.autoTestConfigId,
                }).then(this.nextTick);
            }

            const autoTestRun = this.autoTestConfig && this.autoTestConfig.runs[0];

            this.rubrics = serverRubrics.map(origRow => {
                const row = Object.assign({}, origRow);

                // We map and `Object.assign` here so we have a complete new
                // object to sort.
                row.items = row.items
                    .map(item => Object.assign({}, item))
                    .sort((a, b) => a.points - b.points);

                if (editable && !(row.locked && autoTestRun != null)) {
                    row.items.push(this.getEmptyItem());
                }

                return row;
            });
            this.setOldRubricIds();
        },

        async getAndSetRubrics() {
            if (!this.assignmentId) return;

            await this.forceLoadRubric(this.assignmentId);
            if (this.assignment && this.assignment.rubric) {
                this.setRubricData(this.assignment.rubric);
            } else {
                this.rubrics = [];
            }
        },

        createRow() {
            this.rubrics.push(this.getEmptyRow());
        },

        showDeleteModal() {
            this.$root.$emit('bv::show::modal', 'modal_delete_rubric');
        },

        deleteRubric() {
            return this.$http.delete(`/api/v1/assignments/${this.assignmentId}/rubrics/`);
        },

        deleteFilter(err) {
            if (err.response && err.response.status === 404) {
                return err;
            } else {
                throw err;
            }
        },

        afterDeleteRubric() {
            this.loadAssignments();
            this.rubrics = [];

            this.$root.$emit('bv::hide::modal', 'modal_delete_rubric');

            this.setRubric({
                assignmentId: this.assignmentId,
                rubric: null,
                maxPoints: null,
            });

            // TODO: Improve use of rubric store.
            // Clear rubric from the store so it will be reloaded.
            this.storeClearRubric({ assignmentId: this.assignmentId });
        },

        ensureFixedMaxPoints() {
            if (this.internalFixedMaxPoints === '' || this.internalFixedMaxPoints == null) {
                this.internalFixedMaxPoints = null;
            } else if (Number.isNaN(Number(this.internalFixedMaxPoints))) {
                throw new Error(
                    `The given max points "${this.internalFixedMaxPoints}" is not a number`,
                );
            } else {
                this.internalFixedMaxPoints = Number(this.internalFixedMaxPoints);
            }
        },

        getCheckedRubricRows() {
            const errors = {
                categories: [],
                items: [],
                unnamed: false,
                empty: false,

                hasErrors() {
                    return (
                        this.categories.length || this.items.length || this.empty || this.unnamed
                    );
                },
            };

            const rows = [];
            for (let i = 0, len = this.rubrics.length; i < len; i += 1) {
                const row = this.rubrics[i];

                const res = {
                    header: row.header,
                    description: row.description,
                    items: [],
                };

                if (res.header.length === 0) {
                    errors.unnamed = true;
                }

                const amountOfItems = row.items.length - (this.rowData[row.id].editable ? 1 : 0);
                for (let j = 0; j < row.items.length; j += 1) {
                    const item = row.items[j];
                    if (j >= amountOfItems) {
                        if (item.points || item.description || item.header || item.id) {
                            throw new Error('Something internal went wrong!');
                        }
                        // eslint-disable-next-line
                        continue;
                    }

                    if (Number.isNaN(parseFloat(item.points))) {
                        errors.items.push(
                            `'${row.header || '[No name]'} - ${item.header || '[No name]'}'`,
                        );
                    }
                    item.points = parseFloat(row.items[j].points);

                    res.items.push(item);
                }

                if (res.items.length === 0) {
                    errors.categories.push(row.header || '[No name]');
                }

                if (row.id !== undefined) res.id = row.id;

                rows.push(res);
            }

            if (errors.hasErrors()) {
                throw errors;
            }

            return rows;
        },

        clickSubmit() {
            this.$refs.submitButton.onClick();
        },

        submit() {
            if (!this.editable) {
                throw Error('This rubric editor is not editable.');
            }

            const rows = this.getCheckedRubricRows();
            this.ensureFixedMaxPoints();

            return this.$http.put(`/api/v1/assignments/${this.assignmentId}/rubrics/`, {
                rows,
                max_points: this.internalFixedMaxPoints,
            });
        },

        afterSubmit(response) {
            this.setRubricData(response.data);
            this.setRubric({
                assignmentId: this.assignmentId,
                rubric: response.data,
                maxPoints: this.internalFixedMaxPoints,
            });
            this.forceLoadSubmissions(this.assignmentId);
        },

        addRubricRow() {
            if (!this.editable) {
                throw Error('This rubric editor is not editable.');
            }

            this.$set(this.rubrics, this.rubrics.length, {
                header: '',
                description: '',
                items: [this.getEmptyItem()],
            });
        },

        addItem(i, j) {
            if (!this.editable) {
                throw Error('This rubric editor is not editable.');
            }

            const row = this.rubrics[i];
            if (!this.rowData[row.id].editable) {
                return;
            }

            if (row.items.length - 1 === j) {
                this.$set(this.rubrics[i].items, j + 1, this.getEmptyItem());
            }
        },

        deleteItem(i, j) {
            if (!this.editable) {
                throw Error('This rubric editor is not editable.');
            }

            this.rubrics[i].items.splice(j, 1);
        },

        appendRow() {
            if (!this.editable) {
                throw Error('This rubric editor is not editable.');
            }

            this.rubrics.push(this.getEmptyRow());
            this.$nextTick(() => {
                this.currentCategory = this.rubrics.length - 1;
            });
        },

        deleteRow(index) {
            const row = this.rubrics[index];

            if (!this.editable) {
                throw Error('This rubric editor is not editable.');
            } else if (row.locked) {
                throw Error(`This rubric category is locked by: ${row.locked}.`);
            }

            return index;
        },

        afterDeleteRow(index) {
            this.rubrics.splice(index, 1);
        },

        rubricCategoryTitle(category) {
            return category.header || '<span class="unnamed">Unnamed category</span>';
        },

        calcMaxPoints(rubrics) {
            return rubrics.reduce((cur, row) => {
                const extra = Math.max(
                    ...row.items.map(val => Number(val.points)).filter(item => !Number.isNaN(item)),
                );
                if (extra === -Infinity) {
                    return cur;
                }
                return cur + extra;
            }, 0);
        },

        lockPopover(row) {
            switch (row.locked) {
                case 'auto_test':
                    return this.autoTestLockPopover;
                default:
                    return '';
            }
        },
    },

    components: {
        Icon,
        SubmitButton,
        Loader,
        DescriptionPopover,
        Multiselect,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

@rubric-items-per-row: 4;
@rubric-items-fixed-offset: @rubric-items-per-row + 1;
@rubric-item-min-width: 100% / @rubric-items-per-row;

.rubric-editor {
    margin-bottom: 0;

    .card.rubric-item {
        min-width: @rubric-item-min-width;
        padding: 0.5rem;
        border-bottom: 0;
        border-top: 0;
        border-left: 0;
        border-radius: 0;

        &:nth-child(n + @{rubric-items-fixed-offset}) {
            flex: 0 0 @rubric-item-min-width;
        }

        &:last-child {
            border-right: 0;
        }
    }

    .rubric-items-container {
        border-bottom: 0;
    }

    .rubric-header {
        .default-background;
        padding: 0 !important;
        border-bottom: 0;

        p {
            font-size: 1.1rem;
            line-height: 1.25;
            .default-text-colors;
        }

        input:focus {
            background: #f7f7f9;
        }
    }

    .card,
    card-header {
        border-radius: 0;
        border-top: 0 !important;
        border-left: 0 !important;

        &:not(.tab) {
            border-bottom: 0 !important;
            border-right: 0 !important;
        }
    }

    .rubric-editor {
        .card-header,
        .card-block {
            padding: 0.5rem 0.75rem;
            .rubric-item-wrapper {
                margin: -0.5em;
                padding: 0.5em;
                align-items: center;
            }
        }
    }

    .rubric {
        flex: 1 1 0;
        min-width: 100%;
        background-color: white;
        padding: 1em;
        border: 1px solid transparent !important;

        #app.dark & {
            background-color: @color-primary;
        }

        .item-header-row {
            flex-wrap: nowrap;
        }

        .item-description {
            background-color: @color-lightest-gray;
        }

        .input.disabled {
            #app.dark & {
                color: @text-color-dark !important;
            }

            &.item-description {
                height: 10em;
                overflow: auto;
            }
        }

        .rubric-items-container input,
        .rubric-items-container span.input {
            font-weight: bold;
            background: transparent;

            border: 1px solid transparent !important;
            margin-bottom: 0.2em;

            &:hover:not(.disabled) {
                border-bottom: 1px solid @color-primary-darkest !important;
            }

            &:focus:not(.disabled) {
                border-color: #5cb3fd !important;
                cursor: text;
            }

            &.item-points,
            &.item-header {
                min-width: 0;
                padding: 0.375rem 0.1rem;
            }

            &.item-points {
                flex: 0 0 4rem;
                margin-right: 0.2rem;
                text-align: left;

                &:not(:focus) {
                    border-radius: 0;
                }

                &.disabled {
                    flex-basis: auto;
                    padding-left: 10px;
                }
            }

            &.item-header {
                flex: 1 1 auto;
                margin-left: 0.1rem;

                &:focus {
                    border-top-right-radius: 0.25rem;
                    border-bottom-right-radius: 0.25rem;
                }
            }
        }
    }

    &:not(.editable) .rubric {
        padding-bottom: 0;
    }

    .item-delete-button,
    .item-info-button {
        color: @color-border-gray;
        padding: 0.5rem;
    }

    .item-delete-button:hover {
        .default-text-colors;
        cursor: pointer;
    }

    .item-info-button:hover {
        .default-text-colors;
        cursor: help;
    }
}

.empty {
    padding: 2em;
}

.button-bar,
.card.extra-bar {
    border: 0;

    .card-body {
        justify-content: space-between;
        display: flex;
        flex-direction: row;
        align-items: center;
    }
}

.button-bar {
    margin-top: 1.25rem;

    .override-checkbox {
        justify-content: center;
        display: flex;
        flex: 0 1 auto;
        flex-direction: column;
        align-items: center;

        .max-points-input-group {
            width: auto;
        }
    }

    input {
        width: 5em;
    }
}

.card.extra-bar {
    padding: 0 1rem 1rem 1.5rem;
}

.card-body {
    padding: 0;
}

.danger-buttons {
    .btn {
        width: 50%;
    }

    .btn:first-child {
        border-right: 1px solid white;
    }

    .btn:last-child {
        border-left: 1px solid white;
    }

    #app.dark & .btn {
        border-color: @color-primary;
    }
}

.assignment-alert.alert {
    margin-bottom: 0;
}

.error-popover {
    :last-child {
        margin-bottom: 0 !important;
    }
}
</style>

<style lang="less">
@import '~mixins.less';

.rubric-editor {
    &:not(.editable) {
        .nav-tabs {
            .nav-item:first-child {
                margin-left: 15px;
            }
            .nav-link:hover {
                border-color: @color-light-gray;
            }
        }
    }
    .rubric-items-container .card.rubric-item > .card-block {
        border: 0;
    }

    .nav-tabs {
        .nav-link {
            border-bottom: 0;

            .unnamed {
                color: @color-light-gray;
            }
        }
    }

    .tab-content {
        #app.dark & {
            border-color: @color-primary-darker;
        }
        border: 1px solid #dee2e6;
        border-top: 0;
        border-bottom-right-radius: 0.25rem;
        border-bottom-left-radius: 0.25rem;
    }

    .assignment-selector {
        z-index: 8;
        flex: 1;
        .multiselect__tags {
            border-bottom-right-radius: 0;
            border-top-right-radius: 0;
        }
    }
}
</style>
