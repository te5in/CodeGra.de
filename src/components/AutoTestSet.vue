<template>
<component
    :is="result ? 'div' : 'b-card'"
    no-body
    class="test-group auto-test-set"
    :class="{ editable }">
    <b-card-header v-if="!result" class="auto-test-header" :class="{ editable }">
        Test set
        <div v-if="editable">
            <submit-button
                :submit="deleteSet"
                label="Delete set"
                variant="outline-danger"
                confirm="Are you sure you want to delete this test set and
                            all suits in it."/>
        </div>
    </b-card-header>

    <component :is="result ? 'div' : 'b-card-body'">
        <span v-if="!hasSuites" class="text-muted">
            You have no suites yet. Click the button below to create one.
        </span>

        <masonry v-else
                 :cols="{default: (result ? 1 : 2), [$root.largeWidth]: 1 }"
                 :gutter="30"
                 class="outer-block">
            <auto-test-suite v-for="suite, j in value.suites"
                             v-if="!suite.deleted"
                             :editable="editable"
                             :editing="suite.steps.length === 0"
                             :key="suite.id"
                             :assignment="assignment"
                             :other-suites="otherSuites"
                             :value="value.suites[j]"
                             :result="result"
                             @input="updateSuite(j, $event)" />
        </masonry>

        <div v-if="editable"
                style="float: right;">
            <submit-button
                :submit="addSuite"
                label="Add suite"/>
        </div>
    </component>

    <transition v-if="!isLastSet" :name="animations ? '' : 'setcontinue'">
        <b-card-footer
            v-if="editable"
            class="transition set-continue">
            Only execute other test sets when achieved grade by AutoTest is higher than

            <b-input-group class="input-group">
                <input
                    class="form-control"
                    type="number"
                    v-model="stopPoints"
                    @keyup.ctrl.enter="$refs.submitContinuePointsBtn[i].onClick()"
                    placeholder="0" />
                <b-input-group-append>
                    <submit-button
                        ref="submitContinuePointsBtn"
                        :submit="submitContinuePoints" />
                </b-input-group-append>
            </b-input-group>
        </b-card-footer>

        <b-card-footer
            v-else-if="result"
            class="set-continue">
            <template v-if="value.passed">
                Scored <code>{{ result.setResults[setId].achieved }}</code> points,
                which is greater than <code>{{ value.stop_points }}</code>. Continuing
                with the next set.
            </template>
            <template v-else>
                Scored <code>{{ result.setResults[setId].achieved }}</code> points,
                which is less than <code>{{ value.stop_points }}</code>. No further
                tests will be run.
            </template>
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

        autoTestId() {
            return this.assignment.auto_test_id;
        },

        test() {
            return this.storeTests[this.autoTestId];
        },

        setId() {
            return this.value.id;
        },

        hasSuites() {
            return this.value.suites.filter(s => !s.deleted).length !== 0;
        },

        isLastSet() {
            const i = this.test.sets.indexOf(this.value);
            return !this.test.sets.some((s, j) => j > i && !s.deleted);
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
            return this.storeUpdateAutoTestSet({
                autoTestId: this.autoTestId,
                autoTestSet: this.value,
                setProps: { stop_points: Number(this.stopPoints) },
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
    justify-content: center;

    .input-group {
        width: initial;
        margin-left: 5px;
    }

    code {
        padding: 0 0.25rem;
    }
}

.auto-test-suite:not(:last-child) {
    margin-bottom: 1rem;
}
</style>
