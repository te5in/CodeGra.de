<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="rubric-viewer"
     :class="{ editable }">
    <b-tabs no-fade v-model="current">
        <b-tab class="rubric"
               :head-html="getHeadHtml(rubric)"
               v-for="(rubric, i) in rubrics"
               :key="`rubric-${rubric.id}`">
            <b-card
                class="rubric-category"
                header-class="rubric-category-header"
                body-class="rubric-items">
                <template slot="header">
                    <div class="rubric-category-description">
                        {{ rubric.description }}
                    </div>

                    <icon
                        name="lock"
                        v-if="autoTestProgress[rubric.id]"
                        v-b-popover.hover.top="progressPopover"/>
                </template>

                <div v-if="autoTestProgress[rubric.id]"
                     class="progress">
                    <div ref="progressMeter" class="meter" />
                </div>

                <b-card-group
                    class="rubric-items-group"
                    :class="{ disabled: autoTestProgress[rubric.id] }">
                    <b-card class="rubric-item"
                            v-for="item in rubric.items"
                            :key="`rubric-${rubric.id}-${item.id}`"
                            @click="toggleItem(rubric, item)"
                            :class="{ selected: selected[item.id] }"
                            body-class="rubric-item-body">
                        <div slot="header" class="header">
                            <b class="header-title">{{ item.points }} - {{ item.header }}</b>
                            <div v-if="itemStates[item.id] === '__LOADING__'"
                                 class="rubric-item-icon">
                                <loader :scale="1"/>
                            </div>
                            <div v-else-if="selected[item.id]"
                                class="rubric-item-icon">
                                <icon name="check"/>
                            </div>
                            <div v-else-if="itemStates[item.id]"
                                class="rubric-item-icon">
                                <b-popover show
                                           :target="`rubric-error-icon-${rubric.id}-${item.id}`"
                                           :content="itemStates[item.id]"
                                           placement="top">
                                </b-popover>
                                <icon name="times"
                                    :scale="1"
                                    :id="`rubric-error-icon-${rubric.id}-${item.id}`"
                                    class="text-danger"/>
                            </div>
                        </div>

                        <p class="rubric-item-description">
                            {{ item.description }}
                        </p>
                    </b-card>
                </b-card-group>
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

import { getProps, waitAtLeast } from '../utils';

import Loader from './Loader';

export default {
    name: 'rubric-viewer',

    props: {
        submission: {
            type: Object,
            default: null,
        },
        assignment: {
            type: Object,
            default: null,
        },
        rubric: {
            type: Object,
            default: null,
        },
        editable: {
            type: Boolean,
            default: false,
        },
    },

    data() {
        return {
            rubrics: [],
            selected: {},
            selectedPoints: 0,
            selectedRows: {},
            current: 0,
            maxPoints: 0,
            itemStates: {},
            origSelected: [],
            autoTestResultId: null,
        };
    },

    watch: {
        rubric(rubric) {
            this.rubricUpdated(rubric);
        },

        submission: {
            immediate: true,
            handler() {
                if (this.autoTestConfigId == null) {
                    return;
                }

                Promise.all([
                    this.storeLoadAutoTest({
                        autoTestId: this.autoTestConfigId,
                    }),
                    this.storeLoadAutoTestResult({
                        autoTestId: this.autoTestConfigId,
                        submissionId: this.submissionId,
                    }),
                // eslint-disable-next-line
                ]).then(([_, result]) => {
                    this.autoTestResultId = result.id;
                });
            },
        },

        currentProgress: {
            immediate: true,
            async handler() {
                const cur = this.current;

                if (cur == null || this.currentProgress == null) {
                    return;
                }

                await this.$nextTick();
                const ref = this.$refs.progressMeter[cur];
                ref.style.width = 0;
                await this.$nextTick();
                ref.style.width = `${this.currentProgress}%`;
            },
        },
    },

    computed: {
        ...mapGetters('autotest', {
            allTests: 'tests',
            allResults: 'results',
        }),

        submissionId() {
            return this.submission.id;
        },

        autoTestConfigId() {
            return this.assignment.auto_test_id;
        },

        autoTestConfig() {
            return this.allTests[this.autoTestConfigId];
        },

        autoTestResult() {
            return this.allResults[this.autoTestResultId];
        },

        currentRow() {
            return this.rubrics[this.current];
        },

        currentProgress() {
            return this.currentRow && this.autoTestProgress[this.currentRow.id];
        },

        hasSelectedItems() {
            return Object.keys(this.selected).length !== 0;
        },

        outOfSync() {
            const origSet = new Set(this.origSelected);
            Object.keys(this.selected).forEach(item => {
                if (origSet.has(item)) {
                    origSet.delete(item);
                } else {
                    origSet.add(item);
                }
            });
            return origSet;
        },

        grade() {
            let grade = Math.max(0, this.selectedPoints / this.maxPoints * 10);
            if (Object.keys(this.selected).length === 0) {
                grade = null;
            }
            const maxGrade = (this.assignment && this.assignment.max_grade) || 10;
            if (grade > maxGrade) {
                grade = maxGrade;
            }
            return grade;
        },

        autoTestProgress() {
            const suiteResults = getProps(this, null, 'autoTestResult', 'suiteResults');

            if (!suiteResults) {
                return {};
            }

            const prog = {};
            let i = 0;

            this.autoTestConfig.sets.forEach(set => {
                set.suites.forEach(suite => {
                    const result = suiteResults[suite.id];
                    // FIXME: uncomment, remove line below
                    // prog[suite.rubricRow.id] = (100 * result.achieved / result.possible)
                    // .toFixed(2);
                    prog[this.rubrics[i].id] = (100 * result.achieved / result.possible).toFixed(2);
                    i = (i + 1) % this.rubrics.length;
                });
            });

            return prog;
        },

        progressPopover() {
            if (this.currentProgress == null) {
                return '';
            }

            const index = Math.floor(this.currentRow.items.length * this.currentProgress / 100);
            const points = this.currentRow.items[index].points;

            return `You scored ${this.currentProgress}% in the corresponding AutoTest category, which scores you ${points} points in this rubric category.`;
        },
    },

    mounted() {
        this.rubricUpdated(this.rubric, true);

        this.$root.$on('open-rubric-category', id => {
            this.rubrics.forEach((row, i) => {
                if (row.id === id) {
                    this.current = i;
                }
            });
        });
    },

    destroyed() {
        this.$root.$off('open-rubric-category');
    },

    methods: {
        ...mapActions('autotest', {
            storeLoadAutoTest: 'loadAutoTest',
            storeLoadAutoTestResult: 'loadAutoTestResult',
        }),

        getHeadHtml(rubric) {
            const selected = this.selectedRows[rubric.id];
            const maxPoints = this.$htmlEscape(Math.max(...rubric.items.map(i => i.points)));
            const header =
                this.$htmlEscape(`${rubric.header}`) ||
                '<span class="unnamed">Unnamed category</span>';

            const getFraction = (upper, lower) => `<sup>${upper}</sup>&frasl;<sub>${lower}</sub>`;
            let res;

            if (selected) {
                const selectedPoints = this.$htmlEscape(selected.points);
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
            return this.$http
                .patch(`/api/v1/submissions/${this.submission.id}/rubricitems/`, {
                    items: [],
                })
                .then(() => {
                    this.selected = {};
                    this.selectedPoints = 0;
                    this.selectedRows = {};
                    this.origSelected = [];
                    this.$emit('input', {
                        selected: 0,
                        max: this.maxPoints,
                        grade: null,
                    });
                    return { data: { grade: null } };
                });
        },

        submitAllItems() {
            if (Object.keys(this.outOfSync).length === 0) {
                return Promise.resolve();
            }
            const items = Object.keys(this.selected);

            return this.$http
                .patch(`/api/v1/submissions/${this.submission.id}/rubricitems/`, {
                    items,
                })
                .then(() => {
                    this.origSelected = items;
                });
        },

        rubricUpdated({ rubrics, selected, points }, initial = false) {
            this.rubrics = this.sortRubricItems(rubrics);
            this.origSelected = [];

            if (selected) {
                this.selected = selected.reduce((res, item) => {
                    res[item.id] = item;
                    return res;
                }, {});
                this.origSelected = Object.keys(this.selected);
                this.selectedPoints = selected.reduce((res, item) => res + item.points, 0);
                this.selectedRows = rubrics.reduce((res, row) => {
                    res[row.id] = row.items.reduce(
                        (cur, item) => cur || this.selected[item.id],
                        false,
                    );
                    return res;
                }, {});
            }

            if (points) {
                this.maxPoints = points.max;
                if (!initial) {
                    points.grade = this.grade;
                }
                this.$emit('input', points);
            }
        },

        sortRubricItems(rubrics) {
            return rubrics.map(rubric => {
                rubric.items.sort((x, y) => x.points - y.points);
                return rubric;
            });
        },

        toggleItem(row, item) {
            if (!this.editable || this.autoTestProgress[row.id]) {
                return;
            }

            this.$set(this.itemStates, item.id, '__LOADING__');

            let req;
            const selectItem = !this.selected[item.id];
            const doRequest = UserConfig.features.incremental_rubric_submission;

            if (!doRequest) {
                req = Promise.resolve();
            } else if (selectItem) {
                req = this.$http.patch(
                    `/api/v1/submissions/${this.submission.id}/rubricitems/${item.id}`,
                );
            } else {
                req = this.$http.delete(
                    `/api/v1/submissions/${this.submission.id}/rubricitems/${item.id}`,
                );
            }

            if (doRequest) {
                req = waitAtLeast(500, req);
            }

            req.then(
                () => {
                    row.items.forEach(({ id, points }) => {
                        if (this.selected[id]) {
                            this.selectedPoints -= points;
                        }
                        delete this.selected[id];
                    });
                    if (selectItem) {
                        this.selectedPoints += item.points;
                        this.$set(this.selected, item.id, item);
                    } else {
                        this.$set(this.selected, item.id, undefined);
                        delete this.selected[item.id];
                    }
                    this.$set(this.selectedRows, row.id, selectItem ? item : false);

                    this.$emit('input', {
                        selected: this.selectedPoints,
                        max: this.maxPoints,
                        grade: this.grade,
                    });

                    this.$nextTick(() => {
                        this.$set(this.itemStates, item.id, false);
                        delete this.itemStates[item.id];
                    });
                },
                err => {
                    this.$set(this.itemStates, item.id, err.response.data.message);
                    setTimeout(() => {
                        this.$nextTick(() => {
                            this.$set(this.itemStates, item.id, false);
                            delete this.itemStates[item.id];
                        });
                    }, 3000);
                },
            );
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

    &:not(:last-child) {
        border-right-width: 1px;
    }

    &.selected {
        background-color: @active-color;

        #app.dark & {
            background-color: @color-primary-darkest;
        }
    }

    .editable .rubric-items-group:not(.disabled) & {
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

.rubric-item {
    background-color: transparent;
}

.progress {
    position: absolute;
    top: 0;
    right: 0;
    bottom: 0;
    left: 0;
    background-color: transparent;
    height: 100%;

    .meter {
        background-color: fade(@color-secondary, 10%);
        border-right: 1px solid fade(@color-secondary, 15%);
        width: 0;
        transition: width 1250ms ease-in-out;
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
