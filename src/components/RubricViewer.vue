<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div v-if="rubric"
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
                <b-popover v-if="lockPopover"
                           :show="lockPopoverShown[row.id]"
                           :target="lockPopoverIds[row.id]"
                           :content="lockPopover"
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
                            :class="{ selected: selectedById[item.id] }"
                            body-class="rubric-item-body">
                        <div slot="header" class="header">
                            <b class="header-title">{{ item.points }} - {{ item.header }}</b>
                            <div v-if="itemStates[item.id] === '__LOADING__'"
                                 class="rubric-item-icon">
                                <loader :scale="1"/>
                            </div>
                            <div v-else-if="selectedById[item.id]"
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

                <div v-show="autoTestProgress[row.id] != null" class="progress">
                    <div ref="progressMeter" class="meter" style="width: 0;" />
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
            origSelected: [],
            current: 0,
            itemStates: {},
            lockPopoverShown: {},
        };
    },

    watch: {
        assignment: {
            immediate: true,
            handler() {
                this.storeLoadRubric({
                    assignmentId: this.assignment.id,
                });

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
                });

                if (this.autoTestConfigId) {
                    this.storeLoadAutoTestResult({
                        autoTestId: this.autoTestConfigId,
                        submissionId: this.submission.id,
                        acceptContinuous: true,
                    }).catch(
                        // Autotest hasn't been started yet.
                        () => {},
                    );
                }
            },
        },

        rubricResult: {
            immediate: true,
            handler() {
                this.origSelected = this.$utils.deepCopy(this.selected);
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

        autoTestProgress: {
            immediate: true,
            handler() {
                const cur = this.current;
                this.current = -1;
                this.current = cur;
            },
        },
    },

    computed: {
        ...mapGetters('rubrics', {
            allRubrics: 'rubrics',
            allRubricResults: 'results',
        }),

        ...mapGetters('autotest', {
            allAutoTests: 'tests',
            allAutoTestResults: 'results',
        }),

        rubric() {
            return this.allRubrics[this.assignment.id];
        },

        rubricResult() {
            return this.allRubricResults[this.submission.id];
        },

        selected() {
            return this.$utils.getProps(this.rubricResult, [], 'selected');
        },

        selectedById() {
            return this.selected.reduce((acc, item) => {
                acc[item.id] = item;
                return acc;
            }, {});
        },

        selectedPoints() {
            return this.rubricResult.points;
        },

        selectedRows() {
            return (
                this.rubric &&
                this.rubric.rows.reduce((acc, row) => {
                    acc[row.id] = row.items.reduce(
                        (cur, item) => cur || this.selectedById[item.id],
                        false,
                    );
                    return acc;
                }, {})
            );
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

        currentProgress() {
            return this.currentRow && this.autoTestProgress[this.currentRow.id];
        },

        hasSelectedItems() {
            return this.selected.length !== 0;
        },

        outOfSync() {
            const origSet = new Set(this.origSelected.map(s => s.id));
            this.selected.forEach(({ id }) => {
                if (origSet.has(id)) {
                    origSet.delete(id);
                } else {
                    origSet.add(id);
                }
            });
            return origSet;
        },

        autoTestProgress() {
            const suiteResults = this.$utils.getProps(this, null, 'autoTestResult', 'suiteResults');

            if (!suiteResults) {
                return {};
            }

            const prog = {};

            this.autoTestConfig.sets.forEach(set => {
                set.suites.forEach(suite => {
                    const result = suiteResults[suite.id];
                    if (result != null) {
                        const p = result.achieved / result.possible * 100;
                        prog[suite.rubricRow.id] = p;
                    }
                });
            });

            return prog;
        },

        lockPopover() {
            if (this.rubric == null) {
                return '';
            }

            const lockReason = this.rubric.rows[this.current].locked;

            switch (lockReason) {
                case 'auto_test':
                    return this.autoTestLockPopover;
                default:
                    return '';
            }
        },

        autoTestLockPopover() {
            const selectedInRow = this.selectedRows[this.currentRow.id];
            let msg;

            if (selectedInRow == null || this.currentProgress == null) {
                msg =
                    'This is an AutoTest category. It will be filled in automatically once the ' +
                    'AutoTest for this assignment is finished. ';
            } else {
                msg =
                    `You scored ${this.currentProgress.toFixed(0)}% in the corresponding ` +
                    `AutoTest category, which scores you ${selectedInRow.points} points ` +
                    'in this rubric category. ';
            }

            if (!this.autoTestConfig) {
                return msg;
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

            return msg;
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
            storeLoadRubric: 'loadRubric',
            storeLoadRubricResult: 'loadResult',
            storeUpdateRubricItems: 'updateRubricItems',
            storeToggleRubricItem: 'toggleRubricItem',
        }),

        ...mapActions('autotest', {
            storeLoadAutoTest: 'loadAutoTest',
            storeLoadAutoTestResult: 'loadAutoTestResult',
        }),

        getHeadHtml(row) {
            const selected = this.selectedRows[row.id];
            const maxPoints = this.$utils.htmlEscape(row.maxPoints);
            const header =
                this.$utils.htmlEscape(`${row.header}`) ||
                '<span class="unnamed">Unnamed category</span>';

            const getFraction = (upper, lower) => `<sup>${upper}</sup>&frasl;<sub>${lower}</sub>`;
            let res;

            if (selected) {
                const selectedPoints = this.$utils.htmlEscape(selected.points);
                res = `<span>${header}</span> - <span>${getFraction(
                    selectedPoints,
                    maxPoints,
                )}</span>`;
            } else if (this.editable) {
                res = header;
            } else {
                res = `<span>${header}</span> - <span>${getFraction('Nothing', maxPoints)}<span>`;
            }

            return `<div class="tab-header">${res}</div>`;
        },

        clearSelected() {
            const selected = [];

            // Do not clear items of "locked" rows.
            this.selected.forEach(item => {
                if (this.lockedItemIds.has(item.id)) {
                    selected.push(item);
                }
            });

            return this.storeUpdateRubricItems({
                submissionId: this.submission.id,
                selected,
            }).then(() => {
                this.origSelected = selected;
            });
        },

        submitAllItems() {
            if (this.outOfSync.size === 0) {
                return Promise.resolve();
            }

            return this.storeUpdateRubricItems({
                submissionId: this.submission.id,
                selected: this.selected,
            }).then(() => {
                this.origSelected = this.$utils.deepCopy(this.selected);
            });
        },

        toggleItem(row, item) {
            if (!this.editable || row.locked) {
                return;
            }

            let req = this.storeToggleRubricItem({
                submissionId: this.submission.id,
                row,
                item,
            });

            if (UserConfig.features.incremental_rubric_submission) {
                req = this.$utils.waitAtLeast(500, req);
            }

            req.then(
                () => {
                    delete this.itemStates[item.id];
                    this.$emit('change');
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
            if (!this.visible || this.current == null || this.currentProgress == null) {
                return;
            }

            const cur = this.current;
            await this.$nextTick();
            const ref = this.$refs.progressMeter[cur];

            // Without this the animations don't work.
            // eslint-disable-next-line
            getComputedStyle(ref).width;

            await this.$nextTick();
            ref.style.width = `${this.currentProgress}%`;
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
}
</style>
