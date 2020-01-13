<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div v-if="rubric && originalRubricResult && currentResult"
     class="rubric-viewer"
     :class="{ editable }">
    <b-tabs no-fade v-model="current">
        <b-tab v-for="(row, i) in rubric.rows"
               class="rubric"
               :head-html="getHeadHtml(row)"
               :key="`rubric-${row.id}`">
            <b-card
                class="rubric-category"
                header-class="rubric-category-header"
                body-class="rubric-items"
                @mouseenter="$set(lockPopoverShown, row.id, true)"
                @mouseleave="$delete(lockPopoverShown, row.id)">
                <!-- Try to find a better fix instead of the :key below. It is
                     needed so the popover content updates when the text changes. -->
                <b-popover v-if="row.locked"
                           :key="`${row.id}-${autoTestLockPopover[row.id]}`"
                           :show="lockPopoverShown[row.id]"
                           :target="lockPopoverIds[row.id]"
                           :content="row.locked == 'auto_test' ? autoTestLockPopover[row.id] : ''"
                           triggers=""
                           placement="top" />

                <template slot="header" v-if="row.locked || row.description">
                    <div class="rubric-category-description">
                        {{ row.description }}
                    </div>

                    <icon name="lock"
                          v-if="row.locked"
                          :id="lockPopoverIds[row.id]" />
                </template>

                <b-card-group
                    class="rubric-items-group"
                    :class="{ disabled: row.locked }">
                    <b-card class="rubric-item"
                            v-for="item in row.items"
                            :key="`rubric-${row.id}-${item.id}`"
                            @click="toggleItem(row, item)"
                            :class="{ selected: currentResult.isSelected(item) }"
                            body-class="rubric-item-body">
                        <div slot="header" class="header">
                            <b class="header-title">{{ item.points }} - {{ item.header }}</b>
                            <div v-if="itemStates[item.id] === '__LOADING__'"
                                 class="rubric-item-icon">
                                <loader :scale="1"/>
                            </div>
                            <div v-else-if="currentResult.isSelected(item)"
                                class="rubric-item-icon">
                                <icon name="check"/>
                            </div>
                            <div v-else-if="itemStates[item.id]"
                                class="rubric-item-icon">
                                <b-popover show
                                           :target="`rubric-error-icon-${row.id}-${item.id}`"
                                           :content="itemStates[item.id]"
                                           placement="top">
                                </b-popover>
                                <icon name="times"
                                    :scale="1"
                                    :id="`rubric-error-icon-${row.id}-${item.id}`"
                                    class="text-danger"/>
                            </div>
                        </div>

                        <p class="rubric-item-description">
                            {{ item.description }}
                        </p>
                    </b-card>
                </b-card-group>

                <div v-show="row.id in autoTestProgress" class="progress">
                    <div class="meter" :style="{ width: `${autoTestProgress[row.id]}%` }" />
                </div>
            </b-card>
        </b-tab>
    </b-tabs>
</div>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';

import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/angle-left';
import 'vue-awesome/icons/angle-right';
import 'vue-awesome/icons/times';
import 'vue-awesome/icons/check';
import 'vue-awesome/icons/lock';

import * as constants from '@/constants';

import Loader from './Loader';

export default {
    name: 'rubric-viewer',

    props: {
        assignment: {
            type: Object,
            required: true,
        },
        submission: {
            type: Object,
            required: true,
        },
        editable: {
            type: Boolean,
            default: false,
        },
        visible: {
            type: Boolean,
            default: true,
        },
    },

    data() {
        return {
            id: this.$utils.getUniqueId(),
            current: 0,
            itemStates: {},
            lockPopoverShown: {},
            currentResult: null,
            autoTestProgress: {},
        };
    },

    watch: {
        outOfSync() {
            this.$emit('outOfSyncUpdated', this.outOfSync);
        },

        originalRubricResult: {
            immediate: true,
            handler() {
                if (this.originalRubricResult) {
                    this.currentResult = this.originalRubricResult;
                } else {
                    this.currentResult = null;
                }
                this.$emit('rubricUpdated', this.currentResult);
            },
        },

        assignmentId: {
            immediate: true,
            handler() {
                this.storeLoadRubric(this.assignment.id);

                if (this.autoTestConfigId) {
                    this.storeLoadAutoTest({
                        autoTestId: this.autoTestConfigId,
                    });
                }
            },
        },

        submission: {
            immediate: true,
            handler() {
                this.storeLoadRubricResult({
                    submissionId: this.submission.id,
                    assignmentId: this.assignment.id,
                });

                if (this.autoTestConfigId) {
                    this.storeLoadAutoTestResult({
                        autoTestId: this.autoTestConfigId,
                        submissionId: this.submission.id,
                    }).catch(
                        // Autotest hasn't been started yet.
                        () => {},
                    );
                }
            },
        },

        currentRow: {
            immediate: true,
            handler() {
                this.animateRubricProgress();
            },
        },

        visible: {
            immediate: true,
            handler() {
                this.animateRubricProgress();
            },
        },

        autoTestResult: {
            immediate: true,
            handler(newResult, oldResult) {
                const oldId = this.$utils.getProps(oldResult, null, 'id');
                const newId = this.$utils.getProps(newResult, null, 'id');

                if (oldId !== newId) {
                    this.autoTestProgress = {};
                }
                this.animateRubricProgress();
            },
        },

        currentAutoTestSuitePercentage() {
            this.animateRubricProgress();
        },
    },

    computed: {
        ...mapGetters('rubrics', {
            allRubricResults: 'results',
        }),

        ...mapGetters('autotest', {
            allAutoTests: 'tests',
            allAutoTestResults: 'results',
        }),

        currentAutoTestSuitePercentage() {
            const row = this.currentRow;
            const suite = Object.values(
                this.$utils.getProps(this.autoTestResult, {}, 'suiteResults'),
            ).find(s => s.suite.rubricRow.id === row.id);
            return this.$utils.getProps(suite, null, 'percentage');
        },

        rubric() {
            return this.assignment.rubricModel;
        },

        submissionId() {
            return this.submission.id;
        },

        originalRubricResult() {
            return this.allRubricResults[this.submissionId];
        },

        originalSelectedRubricItems() {
            return this.$utils.getProps(this.originalRubricResult, [], 'selected');
        },

        selectedRows() {
            if (!this.rubric || !this.currentResult) {
                return {};
            }
            return this.rubric.rows.reduce((acc, row) => {
                acc[row.id] = row.items.find(item => this.currentResult.isSelected(item));
                return acc;
            }, {});
        },

        lockedItemIds() {
            if (this.rubric == null) {
                return new Set();
            }

            return new Set(
                this.rubric.rows.reduce((acc, row) => {
                    if (row.locked) {
                        acc.push(...row.items.map(item => item.id));
                    }
                    return acc;
                }, []),
            );
        },

        autoTestConfigId() {
            return this.assignment.auto_test_id;
        },

        autoTestConfig() {
            return this.allAutoTests[this.autoTestConfigId];
        },

        autoTestResult() {
            return Object.values(this.allAutoTestResults).find(
                r => r.submissionId === this.submission.id,
            );
        },

        currentRow() {
            return this.rubric && this.rubric.rows[this.current];
        },

        hasSelectedItems() {
            return this.$utils.getProps(this.currentResult, 0, 'selected', 'length') !== 0;
        },

        outOfSync() {
            const origSet = new Set(this.originalSelectedRubricItems.map(i => i.id));
            this.$utils.getProps(this.currentResult, [], 'selected').forEach(({ id }) => {
                if (origSet.has(id)) {
                    origSet.delete(id);
                } else {
                    origSet.add(id);
                }
            });
            return origSet;
        },

        autoTestLockPopover() {
            const rows = this.$utils.getProps(this, [], 'rubric', 'rows');

            return rows.reduce((acc, row) => {
                if (!row.locked) {
                    return acc;
                }

                const selectedInRow = this.selectedRows[row.id];
                const progress = this.autoTestProgress[row.id];
                let msg;

                if (selectedInRow == null || progress == null) {
                    msg =
                        'This is an AutoTest category. It will be filled in automatically once the ' +
                        'AutoTest for this assignment is finished. ';
                } else {
                    msg =
                        `You scored ${progress.toFixed(0)}% in the corresponding ` +
                        `AutoTest category, which scores you ${selectedInRow.points} points ` +
                        'in this rubric category. ';
                }

                if (!this.autoTestConfig) {
                    acc[row.id] = msg;
                    return acc;
                }

                const gradeCalculation = this.autoTestConfig.grade_calculation;

                switch (gradeCalculation) {
                    case 'full':
                        msg += 'You need to reach the upper bound of a rubric item to achieve it.';
                        break;
                    case 'partial':
                        msg += 'You need to reach the lower bound of a rubric item to achieve it.';
                        break;
                    default:
                        throw new Error('Invalid grade calculation method.');
                }

                acc[row.id] = msg;
                return acc;
            }, {});
        },

        lockPopoverIds() {
            if (this.rubric == null) {
                return {};
            }

            return this.rubric.rows.reduce((acc, row) => {
                acc[row.id] = `rubric-viewer-${this.id}-row-${row.id}`;
                return acc;
            }, {});
        },

        assignmentId() {
            return this.assignment.id;
        },
    },

    mounted() {
        this.$root.$on('open-rubric-category', id => {
            this.current = this.rubric.rows.findIndex(row => row.id === id);
        });
    },

    destroyed() {
        this.$root.$off('open-rubric-category');
    },

    methods: {
        ...mapActions('rubrics', {
            storeLoadRubricResult: 'loadResult',
            storeUpdateRubricItems: 'updateRubricItems',
            storeToggleRubricItem: 'toggleRubricItem',
        }),

        ...mapActions('courses', {
            storeLoadRubric: 'loadRubric',
        }),

        ...mapActions('autotest', {
            storeLoadAutoTest: 'loadAutoTest',
            storeLoadAutoTestResult: 'loadAutoTestResult',
        }),

        getHeadHtml(row) {
            const escape = this.$utils.htmlEscape;
            const selected = this.selectedRows[row.id];
            const maxPoints = escape(row.maxPoints);
            const header =
                escape(`${row.header}`) || '<span class="unnamed">Unnamed category</span>';

            const getFraction = (upper, lower) =>
                `<sup>${escape(upper)}</sup>&frasl;<sub>${escape(lower)}</sub>`;
            let res;

            if (selected) {
                const selectedPoints = escape(selected.points);
                res = `<span>${header}</span> - <span>${getFraction(
                    selectedPoints,
                    maxPoints,
                )}</span>`;
            } else if (this.editable || !this.hasSelectedItems) {
                res = header;
            } else {
                res = `<span>${header}</span> - <span>${getFraction('Nothing', maxPoints)}<span>`;
            }

            if (row.locked === 'auto_test') {
                res += ` ${constants.RUBRIC_BADGE_AT}`;
            }

            return `<div class="tab-header">${res}</div>`;
        },

        clearSelected() {
            const selected = [];

            // Do not clear items of "locked" rows.
            this.currentResult.selected.forEach(item => {
                if (this.lockedItemIds.has(item.id)) {
                    selected.push(item);
                }
            });

            return this.storeUpdateRubricItems({
                submissionId: this.submission.id,
                assignmentId: this.assignment.id,
                selected,
            }).then(() => {
                this.$emit('change', this.currentResult);
            });
        },

        submitAllItems() {
            if (this.outOfSync.size === 0) {
                return Promise.resolve();
            }

            return this.storeUpdateRubricItems({
                submissionId: this.submission.id,
                assignmentId: this.assignment.id,
                selected: this.currentResult.selected,
            });
        },

        toggleItem(row, item) {
            if (!this.editable || row.locked) {
                return;
            }

            let req = new Promise(resolve => {
                this.currentResult = this.currentResult.toggleItem(row, item);
                resolve();
            });

            if (UserConfig.features.incremental_rubric_submission) {
                req = this.$utils.waitAtLeast(
                    500,
                    req.then(() =>
                        this.storeToggleRubricItem({
                            submissionId: this.submission.id,
                            assignmentId: this.assignment.id,
                            row,
                            item,
                        }),
                    ),
                );
            }

            req.then(
                () => {
                    delete this.itemStates[item.id];
                    this.$emit('change', this.currentResult);
                },
                err => {
                    this.itemStates[item.id] = this.$utils.getErrorMessage(err);
                    setTimeout(() => {
                        delete this.itemStates[item.id];
                    }, 5000);
                },
            );
        },

        async animateRubricProgress() {
            const row = this.currentRow;

            if (row == null) {
                return;
            }

            const percentage = this.currentAutoTestSuitePercentage;
            if (percentage == null) {
                this.$delete(this.autoTestProgress, row.id);
                return;
            }

            if (this.autoTestProgress[row.id] == null) {
                // Set to 0 first to make the transition work.
                this.$set(this.autoTestProgress, row.id, 0);
                await this.$afterRerender();
            }

            if (this.visible && row.locked === 'auto_test') {
                await this.$afterRerender();
                this.$set(this.autoTestProgress, row.id, percentage);
            }
        },
    },

    components: {
        Icon,
        Loader,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

@active-color: #e6e6e6;

.rubric-viewer .rubric-category {
    border-top-width: 0;
    border-top-left-radius: 0;
    border-top-right-radius: 0;
}

.rubric-category-header {
    border-top-left-radius: 0;
    border-top-right-radius: 0;
    display: flex;
    align-items: center;

    .rubric-category-description {
        flex: 1 1 auto;
    }
}

.rubric-items {
    padding: 0;
}

.rubric-item {
    border-width: 0;
    border-radius: 0;

    &:not(:last-child) {
        border-right-width: 1px;
    }

    &.selected {
        background-color: @active-color;

        #app.dark & {
            background-color: @color-primary-darkest;
        }
    }

    .rubric-viewer.editable .rubric-items-group:not(.disabled) & {
        cursor: pointer;

        &:hover {
            background-color: @active-color;

            #app.dark & {
                background-color: @color-primary-darkest;
            }
        }
    }

    &-body {
        padding: 0.5rem 0 0 0.75rem;
    }

    &-description {
        display: block;
        max-height: 5rem;
        margin: 0.5rem 0 0;
        padding-right: 0.5rem;
        overflow: auto;
        font-size: smaller;

        &::after {
            content: '';
            display: block;
            height: 0.5rem;
        }
    }

    .rubric-item-body {
        padding-top: 0;
    }

    .card-header {
        background: inherit !important;
        border-bottom: 0;
        padding-bottom: 0;

        .header {
            display: flex;
            background: initial;

            .header-title {
                white-space: nowrap;
                text-overflow: ellipsis;
                overflow: hidden;
                flex: 1 1 auto;
            }
            .rubric-item-icon {
                margin-left: 2px;
            }
        }
    }
}

.rubric-items {
    position: relative;
}

.progress {
    position: absolute;
    left: 0;
    top: 0;
    height: 100%;
    width: 100%;
    box-sizing: content-box;
    border-right: 1px solid transparent;
    border-radius: 0;
    background-color: transparent !important;
    pointer-events: none;

    .meter {
        box-sizing: content-box;
        background-color: fade(@color-secondary, 10%);
        border-right: 1px solid fade(@color-secondary, 15%);
        margin-right: -1px;
        width: 0;
        transition: width 1250ms ease-in-out;

        #app.dark & {
            background-color: fade(white, 10%);
            border-right: 1px solid fade(white, 15%);
        }
    }
}
</style>

<style lang="less">
@import '~mixins.less';

.rubric-viewer .nav-tabs li.nav-item > .nav-link {
    &.active {
        background-color: #f7f7f7;
        border-bottom-color: #f7f7f7;
        font-weight: bold;

        #app.dark & {
            background-color: @color-primary-darker;
        }
    }

    .unnamed {
        color: @color-light-gray;
    }

    .badge {
        transform: translateY(-2px);
    }
}
</style>
