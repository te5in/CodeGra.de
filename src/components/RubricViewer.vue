<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div v-if="rubric && result"
     class="rubric-viewer"
     :class="{ editable }">
    <b-tabs no-fade
            v-model="currentCategory">
        <b-tab v-for="row, i in rubric.rows"
               :head-html="tabTitleHTML(row)"
               :key="`rubric-${row.id}`">
            <component
                v-if="row.type === 'normal' || row.type === 'continuous'"
                :is="`rubric-viewer-${row.type}-row`"
                class="border border-top-0 rounded rounded-top-0"
                :value="internalResult"
                @input="resultUpdated"
                @submit="$emit('submit')"
                :rubric-row="row"
                :assignment="assignment"
                :auto-test="autoTestConfig"
                :auto-test-result="autoTestResult"
                :editable="editable"
                :active="currentCategory === i" />
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
import RubricViewerNormalRow from './RubricViewerNormalRow';
import RubricViewerContinuousRow from './RubricViewerContinuousRow';

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
    },

    data() {
        return {
            id: this.$utils.getUniqueId(),
            currentCategory: 0,
            internalResult: null,
        };
    },

    computed: {
        ...mapGetters('rubrics', {
            storeRubrics: 'rubrics',
            storeRubricResults: 'results',
        }),

        ...mapGetters('autotest', {
            storeAutoTests: 'tests',
            storeAutoTestResults: 'results',
        }),

        rubric() {
            const rubric = this.storeRubrics[this.assignmentId];
            return rubric === constants.NONEXISTENT ? null : rubric;
        },

        result() {
            return this.storeRubricResults[this.submissionId];
        },

        assignmentId() {
            return this.assignment.id;
        },

        submissionId() {
            return this.submission.id;
        },

        autoTestConfigId() {
            return this.assignment.auto_test_id;
        },

        autoTestConfig() {
            return this.storeAutoTests[this.autoTestConfigId];
        },

        autoTestResult() {
            return Object.values(this.storeAutoTestResults).find(
                r => r.submissionId === this.submissionId,
            );
        },
    },

    watch: {
        assignmentId: {
            immediate: true,
            handler() {
                this.storeLoadRubric({
                    assignmentId: this.assignmentId,
                });

                if (this.autoTestConfigId) {
                    this.storeLoadAutoTest({
                        autoTestId: this.autoTestConfigId,
                    });
                }
            },
        },

        submissionId: {
            immediate: true,
            handler() {
                this.storeLoadRubricResult({
                    submissionId: this.submissionId,
                    assignmentId: this.assignmentId,
                });

                if (this.autoTestConfigId) {
                    this.storeLoadAutoTestResult({
                        autoTestId: this.autoTestConfigId,
                        submissionId: this.submissionId,
                    }).catch(
                        // Autotest hasn't been started yet.
                        () => {},
                    );
                }
            },
        },

        result: {
            immediate: true,
            handler() {
                this.internalResult = this.result;
                this.$emit('load', this.result);
            },
        },
    },

    mounted() {
        this.$root.$on('cg::rubric-viewer::open-category', id => {
            this.currentCategory = this.rubric.rows.findIndex(row => row.id === id);
        });
    },

    destroyed() {
        this.$root.$off('cg::rubric-viewer::open-category');
    },

    methods: {
        ...mapActions('rubrics', {
            storeLoadRubric: 'loadRubric',
            storeLoadRubricResult: 'loadResult',
        }),

        ...mapActions('autotest', {
            storeLoadAutoTest: 'loadAutoTest',
            storeLoadAutoTestResult: 'loadAutoTestResult',
        }),

        tabTitleHTML(row) {
            const escape = this.$utils.htmlEscape;
            const toDec = val => escape(this.$utils.toMaxNDecimals(val, 2));
            const makeFraction = (upper, lower) =>
                `<sup>${escape(upper)}</sup>&frasl;<sub>${escape(lower)}</sub>`;

            const parts = [];

            if (row.header) {
                parts.push(escape(row.header));
            } else {
                parts.push('<span class="text-muted font-italic">Unnamed category</span>');
            }

            const selectedItem = this.$utils.getProps(
                this.internalResult,
                null,
                'selected',
                row.id,
            );

            if (selectedItem && !Number.isNaN(Number(selectedItem.multiplier))) {
                const mul = Math.max(0, Math.min(selectedItem.multiplier, 1));
                const points = toDec(selectedItem.points * mul);
                parts.push(`- ${makeFraction(points, row.maxPoints)}`);
            } else if (!this.editable) {
                parts.push(`- ${makeFraction('Nothing', row.maxPoints)}`);
            }

            if (row.locked === 'auto_test') {
                parts.push(constants.RUBRIC_BADGE_AT);
            }

            return parts.join(' ');
        },

        resultUpdated(result) {
            this.internalResult = result;
            this.$emit('input', result);
        },
    },

    components: {
        Icon,
        Loader,
        RubricViewerNormalRow,
        RubricViewerContinuousRow,
    },
};
</script>

<style lang="less">
@import '~mixins.less';

.rubric-viewer {
    .nav-tabs .nav-link {
        padding: 0.25rem 0.5rem;

        &.active {
            background-color: rgba(0, 0, 0, 0.0625);
            border-bottom-width: 0;
        }
    }

    .row-description {
        position: relative;
        max-height: 6.66rem;
        overflow: auto;
        line-height: 1.3;
        background-color: rgba(0, 0, 0, 0.0625);

        .rubric-lock {
            position: sticky;
            top: 0.5rem;
        }
    }

    .progress-meter {
        position: absolute;
        top: 0;
        left: 0;
        height: 100%;
        pointer-events: none;
        background-color: fade(@color-secondary, 10%);
        border-right: 1px solid fade(@color-secondary, 15%);
        color: @color-secondary;
        transition: width @transition-duration;

        #app.dark & {
            background-color: fade(white, 15%);
            border-right: 1px solid fade(white, 25%);
            color: @text-color-dark;
        }

        small {
            position: absolute;
            bottom: 0.5rem;
            right: 0.5rem;
            line-height: 1;
            font-size: 90%;
            text-shadow: -1px 0 rgba(255, 255, 255, 0.75), 0 1px rgba(255, 255, 255, 0.75),
                1px 0 rgba(255, 255, 255, 0.75), 0 -1px rgba(255, 255, 255, 0.75);
            font-weight: bold !important;

            #app.dark & {
                text-shadow: -1px 0 @color-primary, 0 1px @color-primary, 1px 0 @color-primary,
                    0 -1px @color-primary;
            }

            &.progress-0,
            &.progress-1,
            &.progress-2 {
                left: 0.5rem;
            }

            @media @media-no-large {
                &.progress-3,
                &.progress-4,
                &.progress-5,
                &.progress-6 {
                    left: 0.5rem;
                }
            }

            @media @media-small {
                &.progress-7,
                &.progress-8,
                &.progress-9,
                &.progress-10 {
                    left: 0.5rem;
                }
            }
        }
    }
}
</style>
