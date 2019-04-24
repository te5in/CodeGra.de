<template>
<div class="auto-test">
    <b-card header="AutoTest">
    <div class="setup-env-wrapper">
        <h5>Environment setup</h5>
        <b-form-fieldset>
            <label :for="baseSystemId">Base system</label>
            <b-dropdown :text="selectedEnvironmentOption"
                        :id="baseSystemId">
                <b-dropdown-header>Select your environment</b-dropdown-header>
                <b-dropdown-item v-for="optionName in environmentOptions"
                                 @click="selectSetup(optionName)"
                                 :key="optionName">
                    {{ optionName }}
                </b-dropdown-item>
            </b-dropdown>
        </b-form-fieldset>

        <b-form-fieldset>
            <label :for="uploadedFixturesId">
                Uploaded fixtures
            </label>
            <ul style="margin: 0;">
                <li v-for="fixture in uploadedFixtures">
                    <a href="#"
                       @click="openFile(fixture, $event)">
                        {{ fixture.name }}
                    </a>
                </li>
            </ul>
        </b-form-fieldset>

        <b-form-fieldset>
            <label :for="fixtureUploadId">
                Upload fixtures
            </label>
            <multiple-files-uploader
                v-model="fixtures"
                :id="fixtureUploadId"
                no-hard-bottom-corners>
                Click here or drop file(s) add fixtures and test files.
            </multiple-files-uploader>
        </b-form-fieldset>

        <b-form-fieldset>
            <label :for="preStartScriptId">
                Setup script to run
            </label>
            <input class="form-control"
                   :id="preStartScriptId"
                   v-model="startScript"/>
        </b-form-fieldset>
    </div>

    <hr style="margin-bottom: 0;"/>

    <transition :name="disabledAnimations ? '' : 'emptytext'">
        <div class="text-muted empty-text transition"
             v-if="sets.filter(s => !s.deleted).length === 0">
            You have no test sets yet. Click the button below to create one.
        </div>
    </transition>
    <transition-group :name="disabledAnimations ? '' : 'list'">
        <div v-for="set, i in sets"
             v-if="!set.deleted"
             :key="set.id"
             class="list-item transition">
            <b-card header="Test set" class="test-group auto-test-suite">
                <span class="text-muted"
                      v-if="set.suites.filter(s => !s.isEmpty() && !s.deleted).length === 0">
                    You have no suites yet. Click the button below to create one.
                </span>
                <masonry :cols="{default: 2, [$root.largeWidth]: 1, [$root.mediumWidth]: 1 }"
                         :gutter="30"
                         class="outer-block">
                    <auto-test-suite v-for="suite, i in set.suites"
                                     v-if="!suite.deleted"
                                     :editing="suite.steps.length === 0"
                                     :key="suite.id"
                                     :assignment="assignment"
                                     :other-suites="allNonDeletedSuites"
                                     @delete="$set(suite, 'deleted', true)"
                                     v-model="set.suites[i]"/>
                </masonry>
                <b-button-toolbar justify class="test-suites-button-wrapper">
                    <div class="btn-wrapper">
                        <submit-button
                            :submit="() => deleteSet(i)"
                            :wait-at-least="0"
                            label="Delete set"
                            variant="outline-danger"
                            confirm="Are you sure you want to delete this test set and
                                     all suits in it."/>
                    </div>
                    <div class="btn-wrapper">
                        <submit-button
                            :submit="() => addSuite(i)"
                            label="Add suite"
                            :wait-at-least="0"/>
                    </div>
                </b-button-toolbar>
            </b-card>
        </div>
    </transition-group>
    <div class="add-btn-wrapper transition">
        <submit-button :submit="addSet" label="Add set"
                       class="transition"/>
    </div>

    <hr/>

    <div class="finalizing-script-wrapper">
        <h5>Finalizing script</h5>
    </div>
    <div slot="footer">
        Hello
    </div>
    </b-card>
</div>
</template>

<script>
import { getUniqueId } from '@/utils';

import AutoTestSuite from './AutoTestSuite';
import SubmitButton from './SubmitButton';
import MultipleFilesUploader from './MultipleFilesUploader';


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
                'Python 2.7',
                'Python 3.5',
                'Python 3.6',
                'Python 3.7',
                'Java 1.6',
                'Java 1.7',
                'R',
            ],
            startScript: '#!/bin/bash\n\n',
            fixtures: [],
            selectedEnvironmentOption: 'Select config file',
            sets: [],
            disabledAnimations: true,
            uploadedFixtures: [{
                name: 'test1.sh',
                id: 12,
            }],

            baseSystemId: `auto-test-base-system-${getUniqueId()}`,
            fixtureUploadId: `auto-test-base-upload-${getUniqueId()}`,
            uploadedFixturesId: `auto-test-base-fixtures-${getUniqueId()}`,
            preStartScriptId: `auto-test-base-pre-start-script-${getUniqueId()}`,
        };
    },

    mounted() {
        this.disabledAnimations = false;
    },

    methods: {
        openFile(_, event) {
            event.preventDefault();
        },

        selectSetup(selectedName) {
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

        addSuite(index) {
            this.sets[index].suites.push(this.createEmptySuite());
            this.$set(this.sets, index, this.sets[index]);
        },

        deleteSet(index) {
            const res = Promise.resolve();
            res.then(async () => {
                await this.$nextTick();
                this.$set(this.sets[index], 'deleted', true);
            });
            return res;
        },

        addSet() {
            this.sets.push({
                suites: [],
                id: getUniqueId(),
            });
            this.sets = this.sets;
        },
    },

    computed: {
        allNonDeletedSuites() {
            return this.sets.reduce(
                (res, set) => {
                    if (!set.deleted) {
                        res.push(...set.suites.filter(s => !s.deleted));
                    }
                    return res;
                },
                [],
            );
        },
    },

    components: {
        AutoTestSuite,
        SubmitButton,
        MultipleFilesUploader,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.auto-test-suite:not(.empty-auto-test-suite) {
    margin-bottom: 1rem;
}


.transition {
    transition: all .3s linear;
}

.list-item {
    margin-top: 1rem;
}

.test-suites-button-wrapper {
    margin-top: 1rem;
}

.test-suites-button-wrapper,
.add-btn-wrapper {
    display: flex;
    justify-content: right;

    .btn {
        align-self: flex-end;
    }
}


.list-enter-active {
    max-height: 15rem;
    overflow-y: hidden;
    margin-top: 1rem;
}
.list-leave-active {
    max-height: 15rem;
}
.list-leave-to {
    opacity: 0;
    max-height: 0;
    overflow-y: hidden;
}

.list-enter {
    max-height: 0;
    margin-top: 1.5rem;
    overflow-y: hidden;
}

.emptytext-enter-active,
.emptytext-leave-active {
    max-height: 2rem;
    margin-bottom: 0;
}

.emptytext-enter,
.emptytext-leave-to {
    max-height: 0;
    overflow-y: hidden;
    margin: 0 !important;
}

.empty-text {
    margin-top: 1rem;
}
</style>
