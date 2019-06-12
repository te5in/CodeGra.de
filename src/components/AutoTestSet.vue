<template>
<component :is="result ? 'div' : 'b-card'"
           no-body
           class="auto-test-set"
           :class="{ 'mt-3': !result }">
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

        <masonry :cols="{default: (result ? 1 : 2), [$root.largeWidth]: 1 }"
                 :gutter="30" >
            <auto-test-suite v-for="suite, j in value.suites"
                             v-if="!suite.deleted"
                             :editable="editable"
                             :editing="suite.steps.length === 0"
                             :key="`suite-${suite.id}`"
                             :assignment="assignment"
                             :other-suites="otherSuites"
                             :value="value.suites[j]"
                             :result="result"
                             @input="updateSuite(j, $event)" />
        </masonry>

        <b-button-toolbar v-if="editable"
                          class="justify-content-end">
            <submit-button :submit="addSuite"
                           label="Add category"/>
        </b-button-toolbar>
    </component>

    <transition v-if="!isLastSet" :name="animations ? '' : 'setcontinue'">
        <template v-if="result">
            <template v-if="stopPoints > 0">
                <b-alert show
                        v-if="setResult.finished"
                        :variant="setResult.achieved >= stopPoints ? 'success' : 'danger'"
                        class="mt-3">
                    Scored <code>{{ setResult.achieved }}</code> points, which is

                    <template v-if="setResult.achieved >= stopPoints">
                        greater than or equal to <code>{{ stopPoints }}</code>.
                        Continuing with the next level.
                    </template>

                    <template v-else>
                        less than <code>{{ stopPoints }}</code>.
                        No further tests will be run.
                    </template>
                </b-alert>

                <div v-else class="border rounded my-3 p-3">
                    Only execute further levels if total points achieved by AutoTest is higher than
                    <code>{{ stopPoints }}</code>
                </div>
            </template>
        </template>

        <b-card-footer v-else-if="editable" class="text-muted font-italic py-1 set-continue">
            Only execute further levels if total points achieved by AutoTest is higher than

            <b-input-group class="ml-1">
                <input class="form-control"
                       type="number"
                       v-model="stopPoints"
                       placeholder="0"
                       @keyup.ctrl.enter="$refs.submitContinuePointsBtn.onClick()" />

                <b-input-group-append>
                    <submit-button
                        ref="submitContinuePointsBtn"
                        :submit="submitContinuePoints" />
                </b-input-group-append>
            </b-input-group>
        </b-card-footer>

        <b-card-footer v-else-if="stopPoints > 0" class="text-muted font-italic py-1">
            Only execute further levels if total achieved points by AutoTest is higher than
            <code>{{ stopPoints }}</code>
        </b-card-footer>
    </transition>
</component>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';
import AutoTestSuite from './AutoTestSuite';
import SubmitButton from './SubmitButton';

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

        animations: {
            type: Boolean,
            default: true,
        },
    },

    data() {
        return {
            stopPoints: this.value.stop_points,
        };
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
            return this.value.suites.filter(s => s.isValid()).length !== 0;
        },

        setIndex() {
            return this.test.sets.indexOf(this.value);
        },

        isLastSet() {
            return !this.test.sets.some((s, j) => j > this.setIndex && !s.deleted);
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

            const prevSetHasGreater = this.test.sets.some(
                (s, j) => j < this.setIndex && s.stop_points > stopPoints && stopPoints !== 0,
            );
            if (prevSetHasGreater) {
                throw new RangeError(
                    'The value must be greater than or equal to all previous levels.',
                );
            }

            const nextHasSmaller = this.test.sets.some(
                (s, j) => j > this.setIndex && s.stop_points < stopPoints && s.stop_points !== 0,
            );
            if (nextHasSmaller) {
                throw new RangeError(
                    'The value must be less than or equal to all following levels.',
                );
            }

            return this.storeUpdateAutoTestSet({
                autoTestId: this.autoTestId,
                autoTestSet: this.value,
                setProps: { stop_points: stopPoints },
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
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.transition {
    transition: all 0.3s linear;
}

.setcontinue-enter-active,
.setcontinue-leave-active {
    max-height: 2rem;
    overflow-y: hidden;
    margin-bottom: 0;
}

.setcontinue-enter-active,
.setcontinue-leave-active {
    max-height: 4rem;
}

.setcontinue-enter,
.setcontinue-leave-to {
    padding-top: 0 !important;
    padding-bottom: 0 !important;
}

.setcontinue-enter,
.setcontinue-leave-to {
    max-height: 0;
    overflow-y: hidden;
    margin: 0 !important;
}

.set-continue {
    display: flex;
    align-items: center;
    justify-content: space-between;

    .input-group {
        width: initial;
    }
}

.auto-test-suite:not(.empty-auto-test-suite),
.auto-test-suite:not(:last-child) {
    margin-bottom: 1rem;
}

.auto-test {
    &:not(.config-editable) .auto-test-suite:last-child {
        margin-bottom: 0;
    }

    @media @media-large {
        &.config-editable .auto-test-suite:nth-last-child(2) {
            margin-bottom: 0;
        }
    }
}
</style>
