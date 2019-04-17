<template>
<div class="auto-test">
    <div class="setup-env-wrapper">
        <h5>Environment setup</h5>
        <b-dropdown :text="selectedEnvironmentOption">
            <b-dropdown-header>Select your environment</b-dropdown-header>
            <b-dropdown-item v-for="optionName in environmentOptions"
                             @click="selectSetup(false, optionName)"
                             :key="optionName">
                {{ optionName }}
            </b-dropdown-item>
            <b-dropdown-divider/>
            <b-dropdown-item @click="selectSetup(true, 'Custom config')">Custom config</b-dropdown-item>
        </b-dropdown>
    </div>

    <hr/>

    <b-card header="Test set" class="test-group auto-test-suite">
        <span class="text-muted"
              v-if="suites.filter(s => !s.isEmpty() && !s.deleted).length === 0">
            You have no suites yet.
        </span>
        <masonry :cols="{default: 2, [$root.largeWidth]: 1, [$root.mediumWidth]: 1 }"
                 :gutter="30"
                 class="outer-block">
            <auto-test-suite v-for="suite, i in suites"
                             v-if="!suite.deleted"
                             :editing="suite.steps.length === 0"
                             :key="suite.id"
                             :assignment="assignment"
                             :other-suites="suites.filter(s => s.id != suite.id)"
                             @delete="$set(suite, 'deleted', true)"
                             v-model="suites[i]"/>
        </masonry>
        <div class="add-btn-wrapper">
            <submit-button :submit="addSuite" label="Add suite"/>
        </div>
    </b-card>

    <b-card header="Condition" class="test-group">
        ....
    </b-card>

    <hr/>

    <div class="test-group">
        <h5>Test Set</h5>
        <masonry :cols="{default: 2, [$root.largeWidth]: 1, [$root.mediumWidth]: 1 }"
                 :gutter="30"
                 class="outer-block">
            <auto-test-suite v-for="suite, i in suites"
                             :key="suite.id"
                             :assignment="assignment"
                             :other-suites="suites.filter(s => s.id != suite.id)"
                             v-if="!suite.deleted"
                             @delete="$set(suite, 'deleted', true)"
                             v-model="suites[i]"/>
        </masonry>
        <div class="add-btn-wrapper">
            <submit-button :submit="addSuite" label="Add suite"/>
        </div>
    </div>

    <hr/>

    <div class="finalizing-script-wrapper">
        <h5>Finalizing script</h5>
    </div>
</div>
</template>

<script>
import { getUniqueId } from '@/utils';

import AutoTestSuite from './AutoTestSuite';
import SubmitButton from './SubmitButton';


export default {
    name: 'auto-test',

    props: {
        assignment: {
            type: Object,
            required: true,
        },
    },

    data() {
        return {
            environmentOptions: [
                'Python 2',
                'Python 3.5',
                'Python 3.6',
                'Python 3.7',
                'Java 1.6',
            ],
            selectedEnvironmentOption: 'Select config file',
            suites: [],
        };
    },

    methods: {
        selectSetup(customConfig, selectedName) {
            this.selectedEnvironmentOption = selectedName;
        },

        createEmptySuite() {
            return {
                steps: [],
                id: getUniqueId(),
                rubricCategory: {},
                editing: true,
                isEmpty() {
                    return this.steps.length === 0;
                },
            };
        },

        addSuite() {
            this.suites.push(this.createEmptySuite());
            this.$set(this, 'suites', this.suites);
        },
    },

    components: {
        AutoTestSuite,
        SubmitButton,
    },
};
</script>

<style lang="less" scoped>
.auto-test-suite:not(.empty-auto-test-suite) {
    margin-bottom: 1rem;
}

.add-btn-wrapper {
    display: flex;
    justify-content: right;

    .btn {
        align-self: flex-end;
    }
}
</style>
