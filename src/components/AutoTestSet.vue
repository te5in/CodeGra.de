<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<component :is="result ? 'div' : 'b-card'"
           no-body
           class="auto-test-set" >
    <b-card-header v-if="!result"
                   class="d-flex justify-content-between align-items-center"
                   :class="{ 'py-1': editable }">
        Level {{ setIndex + 1 }}

        <template v-if="editable">
            <submit-button :submit="deleteSet"
                           label="Delete level"
                           variant="outline-danger"
                           confirm="Are you sure you want to delete this level and all categories in it?"/>
        </template>
    </b-card-header>

    <component :is="result ? 'div' : 'b-card-body'">
        <span v-if="!hasSuites && !result" class="text-muted font-italic">
            This level has no categories yet.

            <template v-if="editable">
                Click the button below to create one.
            </template>
        </span>

        <masonry :gutter="30" :cols="{default: (result ? 1 : 2), [$root.largeWidth]: 1 }">
            <auto-test-suite v-for="suite, j in value.suites"
                             class="mb-3"
                             :editable="editable"
                             :editing="suite.steps.length === 0"
                             :key="suite.id"
                             :assignment="assignment"
                             :other-suites="otherSuites"
                             :value="value.suites[j]"
                             :result="result"
                             :is-continuous="isContinuous"
                             @input="updateSuite(j, $event)" />
        </masonry>

        <b-button-toolbar v-if="editable"
                          class="justify-content-end">
            <submit-button :submit="addSuite"
                           label="Add category"/>
        </b-button-toolbar>
    </component>

    <transition name="set-continue">
        <template v-if="!isLastSet">
            <template v-if="result">
                <template v-if="stopPoints > 0">
                    <b-alert show
                             v-if="setResult.finished"
                             :variant="setPassed ? 'success' : 'danger'">
                        You scored <code class="percentage">{{ $utils.toMaxNDecimals(100 * setResult.percentage, 2) }}%</code> of the
                        <code class="percentage">{{ stopPoints }}%</code> required to continue.

                        <template v-if="!setPassed">
                            No further tests will be run.
                        </template>
                    </b-alert>

                    <div v-else class="border rounded mb-3 p-3">
                        You need to score <code>{{ stopPoints }}%</code> of the points possible
                        up to this point for AutoTest to continue past here.
                    </div>
                </template>
            </template>

            <b-card-footer v-else-if="editable || stopPoints > 0"
                           class="set-continue"
                           :class="editable ? 'py-1' : 'py-2'">
                <span>
                    Only execute further levels if total percentage of points achieved by AutoTest
                    is higher than or equal to

                    <code v-if="!editable">{{ stopPoints }}%</code>

                    <description-popover hug-text>
                        <template slot="description">
                            AutoTest will stop if the percentage of points achieved is less than
                            the filled in amount.
                        </template>
                    </description-popover>
                </span>

                <b-input-group v-if="editable"
                               class="ml-1">
                    <input class="form-control"
                           type="number"
                           v-model="stopPoints"
                           placeholder="0"
                           min="0"
                           max="100"
                           @keyup.ctrl.enter="$refs.submitContinuePointsBtn.onClick()" />

                    <b-input-group-append>
                        <submit-button ref="submitContinuePointsBtn"
                                       :submit="submitContinuePoints" />
                    </b-input-group-append>
                </b-input-group>
            </b-card-footer>
        </template>
    </transition>
</component>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';

import AutoTestSuite from './AutoTestSuite';
import SubmitButton from './SubmitButton';
import DescriptionPopover from './DescriptionPopover';

export default {
    name: 'auto-test-set',

    props: {
        value: {
            type: Object,
            required: true,
        },
        assignment: {
            type: Object,
            required: true,
        },
        editable: {
            type: Boolean,
            default: false,
        },
        result: {
            type: Object,
            default: null,
        },
        otherSuites: {
            type: Array,
            required: true,
        },
        isContinuous: {
            type: Boolean,
            default: false,
        },
    },

    data() {
        return {
            stopPoints: 0,
        };
    },

    watch: {
        value: {
            immediate: true,
            handler() {
                this.stopPoints = 100 * this.value.stop_points;
            },
        },
    },

    computed: {
        ...mapGetters('autotest', {
            storeTests: 'tests',
            storeResults: 'results',
        }),

        permissions() {
            return this.$utils.getProps(this, {}, 'assignment', 'course', 'permissions');
        },

        autoTestId() {
            return this.assignment.auto_test_id;
        },

        test() {
            return this.storeTests[this.autoTestId];
        },

        setId() {
            return this.value.id;
        },

        setResult() {
            return this.result.setResults[this.setId];
        },

        hasSuites() {
            return this.value.suites.filter(s => !s.isEmpty()).length !== 0;
        },

        setIndex() {
            return this.test.sets.indexOf(this.value);
        },

        isLastSet() {
            return !this.test.sets.some((s, j) => j > this.setIndex && !s.deleted);
        },

        setPassed() {
            return 100 * this.setResult.percentage >= this.stopPoints;
        },
    },

    methods: {
        ...mapActions('autotest', {
            storeDeleteAutoTestSet: 'deleteAutoTestSet',
            storeUpdateAutoTestSet: 'updateAutoTestSet',
            storeCreateAutoTestSuite: 'createAutoTestSuite',
            storeDeleteAutoTestSuite: 'deleteAutoTestSuite',
            storeUpdateAutoTestSuite: 'updateAutoTestSuite',
        }),

        deleteSet() {
            return this.storeDeleteAutoTestSet({
                autoTestId: this.autoTestId,
                setId: this.setId,
            });
        },

        submitContinuePoints() {
            const stopPoints = Number(this.stopPoints);

            if (stopPoints > 100) {
                throw new Error('The value cannot be higher than 100.');
            } else if (stopPoints < 0) {
                throw new Error('The value cannot be less than 0.');
            }

            return this.storeUpdateAutoTestSet({
                autoTestId: this.autoTestId,
                autoTestSet: this.value,
                setProps: { stop_points: stopPoints / 100 },
            });
        },

        addSuite() {
            return this.storeCreateAutoTestSuite({
                autoTestId: this.autoTestId,
                autoTestSet: this.value,
            });
        },

        updateSuite(index, suite) {
            return this.storeUpdateAutoTestSuite({
                autoTestSet: this.value,
                index,
                suite,
            });
        },
    },

    components: {
        AutoTestSuite,
        SubmitButton,
        DescriptionPopover,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.set-continue {
    display: flex;
    align-items: center;
    justify-content: space-between;
    overflow: hidden;

    .input-group {
        width: initial;
    }
}

.set-continue-enter-active,
.set-continue-leave-active {
    transition: max-height @transition-duration;
    overflow: hidden;
}

.set-continue-enter,
.set-continue-leave-to {
    max-height: 0;
}

.set-continue-enter-to,
.set-continue-leave {
    max-height: 6rem;
}

.auto-test-suite {
    margin-bottom: 1rem !important;

    .empty {
        display: none;
    }

    .auto-test:not(.editable) .auto-test-set.card &:last-child,
    .auto-test:not(.editable) .auto-test-set:last-child &:last-child {
        margin-bottom: 0 !important;
    }
}

#app.dark .alert.alert-danger code.percentage {
    color: @text-color-dark;
}
</style>
