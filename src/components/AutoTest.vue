<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<b-alert v-if="message && message.isError"
         show
         variant="danger"
         class="m-3">
    {{ message.text }}
</b-alert>
<div v-else-if="message" class="text-muted font-italic p-3">
    {{ message.text }}
</div>

<loader v-else-if="loading" class="my-3" />

<div v-else class="auto-test" :class="{ editable: configEditable }">
    <transition-group v-if="!singleResult" name="auto-test-runs">
        <!-- Use `$utils.getProps` here instead of `!!autoTestRun` in the v-if above
             because transiton-group does not work for the first item if it suddenly
             renders because its v-if condition becomes true. -->
        <auto-test-run v-for="run in $utils.getProps(test, [], 'runs')"
                       :key="run.id"
                       class="mb-3"
                       :class="{ border: editable }"
                       :assignment="assignment"
                       :auto-test="test"
                       :run="run"
                       :editable="editable"
                       @open-result="openResult"
                       @results-deleted="afterDeleteResults" />
    </transition-group>

    <b-card no-body :class="{ 'border-0': !editable }">
        <collapse v-model="configCollapsed" :disabled="!isConfigCollapsible">
            <b-card-header v-if="editable"
                           slot="handle"
                           class="py-1 d-flex justify-content-between align-items-center">
                <span class="toggle">
                    <icon v-if="isConfigCollapsible" name="chevron-down" :scale="0.75" />
                    Configuration
                </span>

                <b-button-toolbar v-if="showCreateButton">
                    <div v-b-popover.hover.top="createAutoTestPopover">
                        <submit-button label="Create AutoTest"
                                       :disabled="canCreateAutoTest"
                                       :submit="createAutoTest"
                                       @after-success="afterCreateAutoTest"/>
                    </div>
                </b-button-toolbar>

                <b-button-toolbar v-else>
                    <div v-b-popover.hover.top="runAutoTestPopover">
                        <submit-button label="Run"
                                       :disabled="!!runAutoTestPopover"
                                       :submit="runAutoTest"
                                       @after-success="afterRunAutoTest" />
                    </div>

                    <div v-b-popover.hover.top="deleteAutoTestPopover">
                        <submit-button label="Delete"
                                       variant="danger"
                                       class="ml-1"
                                       confirm="Are you sure you want to delete this AutoTest configuration?"
                                       :disabled="!canDeleteAutoTest"
                                       :submit="deleteAutoTest"
                                       @after-success="afterDeleteAutoTest"/>
                    </div>
                </b-button-toolbar>
            </b-card-header>

            <b-card-body v-if="test == null"
                         class="text-muted font-italic">
                This assignment does not have an AutoTest configuration.
            </b-card-body>
            <b-card-body v-else class="p-3">
                <b-card no-body class="setup-env-wrapper mb-3">
                    <collapse v-model="setupCollapsed" :disabled="!singleResult">
                        <b-card-header slot="handle">
                            <span class="toggle">
                                <icon v-if="singleResult" name="chevron-down" :scale="0.75" />
                                Setup
                            </span>
                        </b-card-header>

                        <b-card-body>
                            <b-form-fieldset>
                                <label :for="gradeCalculationId">
                                    Rubric calculation

                                    <description-popover hug-text>
                                        Determines how each category in a
                                        rubric should be filled in by AutoTest.
                                        If this is <b>minimum</b>, a rubric
                                        category's item will be chosen when the
                                        lower bound of this item is reached
                                        (e.g.  when a category has 4 items and
                                        75% of the tests succeed, the maximum
                                        item is filled in). If this is
                                        <b>maximum</b>, a category's item will
                                        be chosen when the upper bound of this
                                        item is reached.
                                    </description-popover>
                                </label>
                                <br>

                                <b-input-group>
                                    <b-radio-group stacked
                                                   class="p-0 form-control"
                                                   :class="{
                                                       'rounded-left': configEditable,
                                                       'readably-disabled': !configEditable,
                                                   }"
                                                   v-model="internalTest.grade_calculation"
                                                   :disabled="!configEditable"
                                                   :options="gradeCalculationOptions" />

                                    <submit-button v-if="configEditable"
                                                   class="rounded-right"
                                                   :disabled="internalTest.grade_calculation == null"
                                                   :submit="() => submitProp('grade_calculation')"
                                                   ref="gradeCalculationBtn" />
                                </b-input-group>
                            </b-form-fieldset>

                            <p v-if="!configEditable && !hasEnvironmentSetup"
                               class="mb-0 text-muted font-italic">
                                Uploaded fixtures or setup scripts and their output would normally
                                be shown here. However, none were uploaded, so there is nothing to
                                show.
                            </p>

                            <!-- Use v-show instead of v-if to make the transition-group work. -->
                            <b-form-fieldset v-show="canViewFixtures">
                                <label>
                                    Uploaded fixtures
                                </label>

                                <transition-group name="fixture-list" tag="ul" class="fixture-list form-control p-0 mb-0">
                                    <li v-for="fixture, index in test.fixtures"
                                        class="border-bottom"
                                        :key="fixture.id">
                                        <div class="px-3 py-1 d-flex align-items-center justify-content-between">
                                            <a v-if="canViewFixture(fixture)"
                                                class="flex-grow-1"
                                                href="#"
                                                @click.capture.prevent.stop="openFixture(fixture)">
                                                {{ fixture.name }}
                                            </a>
                                            <span v-else>
                                                {{ fixture.name }}
                                            </span>

                                            <template v-if="configEditable">
                                                <b-button-group>
                                                    <submit-button
                                                        :variant="fixture.hidden ? 'primary' : 'secondary'"
                                                        :submit="() => toggleHidden(index)"
                                                        size="sm">
                                                        <icon :name="fixture.hidden ? 'eye-slash' : 'eye'" />
                                                    </submit-button>
                                                    <submit-button
                                                        variant="danger"
                                                        confirm="Are you sure you want to delete this fixture?"
                                                        size="sm"
                                                        :submit="() => removeFixture(index)">
                                                        <icon name="times"/>
                                                    </submit-button>
                                                </b-button-group>
                                            </template>

                                            <icon v-else-if="fixture.hidden"
                                                    name="eye-slash"
                                                    v-b-popover.window.top.hover="`This fixture is hidden. ${
                                                        singleResult && !canViewFixture(fixture) ? 'You' : 'Students'
                                                    } may not view its contents.`"/>
                                        </div>
                                    </li>
                                </transition-group>
                            </b-form-fieldset>

                            <b-form-fieldset v-if="configEditable">
                                <label :for="fixtureUploadId">
                                    Upload fixtures

                                    <description-popover hug-text>
                                        <template slot="description">
                                            Upload all files you want to be available on the
                                            AutoTest Virtual Machine. Archives will not be extracted
                                            automatically. Make sure to upload your setup script
                                            here as well. These files will be put in the
                                            <code>$FIXTURES</code> directory.
                                        </template>
                                    </description-popover>
                                </label>

                                <multiple-files-uploader
                                    v-model="newFixtures"
                                    :id="fixtureUploadId">
                                    Click here or drop file(s) add fixtures and test files.
                                </multiple-files-uploader>

                                <b-input-group class="upload-fixtures-wrapper justify-content-end border rounded-bottom">
                                    <submit-button
                                        :disabled="newFixtures.length === 0"
                                        @after-success="afterAddFixtures"
                                        class="rounded-0"
                                        :submit="addFixtures" />
                                </b-input-group>
                            </b-form-fieldset>

                            <b-form-fieldset v-if="configEditable || test.run_setup_script">
                                <label :for="globalPreStartScriptId">
                                    Global setup script to run

                                    <description-popover hug-text>
                                        <template slot="description">
                                            Input a bash command to run your global setup script.
                                            This script will be run at the beginning of the AutoTest
                                            run. Put all your global setup in this script, such as
                                            installing packages and compiling fixtures. Don't put
                                            any student-specific setup in this script.
                                        </template>
                                    </description-popover>
                                </label>

                                <template v-if="configEditable">
                                    <b-input-group>
                                        <input class="form-control"
                                                @keydown.ctrl.enter="$refs.runSetupScriptBtn.onClick"
                                                :id="globalPreStartScriptId"
                                                v-model="internalTest.run_setup_script"/>

                                        <b-input-group-append>
                                            <submit-button
                                                :submit="() => submitProp('run_setup_script')"
                                                ref="runSetupScriptBtn"/>
                                        </b-input-group-append>
                                    </b-input-group>
                                </template>

                                <div v-else>
                                    <code>{{ test.run_setup_script }}</code>

                                    <template v-if="result && canViewAutoTest">
                                        <b-tabs no-fade>
                                            <b-tab title="stdout">
                                                <inner-code-viewer class="rounded border"
                                                                   :assignment="assignment"
                                                                   :code-lines="prepareOutput(autoTestRun.setupStdout)"
                                                                   :file-id="-1"
                                                                   :feedback="{}"
                                                                   :start-line="0"
                                                                   :show-whitespace="true"
                                                                   :warn-no-newline="false"
                                                                   :empty-file-message="'No output.'" />
                                            </b-tab>

                                            <b-tab title="stderr">
                                                <inner-code-viewer class="rounded border"
                                                                   :assignment="assignment"
                                                                   :code-lines="prepareOutput(autoTestRun.setupStderr)"
                                                                   :file-id="-1"
                                                                   :feedback="{}"
                                                                   :start-line="0"
                                                                   :show-whitespace="true"
                                                                   :warn-no-newline="false"
                                                                   :empty-file-message="'No output.'" />
                                            </b-tab>
                                        </b-tabs>
                                    </template>
                                </div>
                            </b-form-fieldset>

                            <b-form-fieldset v-if="configEditable || test.setup_script">
                                <label :for="preStartScriptId">
                                    Per-student setup script to run

                                    <description-popover hug-text>
                                        <template slot="description">
                                            Input a bash command to run your setup script that will
                                            be run for each student specifically.  This command will
                                            be run in the home directory
                                            (<code>/home/codegrade/</code>). You can access your
                                            fixtures through the <code>$FIXTURES</code> environment
                                            variable.
                                        </template>
                                    </description-popover>
                                </label>

                                <template v-if="configEditable">
                                    <b-input-group>
                                        <input class="form-control"
                                               @keydown.ctrl.enter="$refs.setupScriptBtn.onClick"
                                               :id="preStartScriptId"
                                               v-model="internalTest.setup_script"/>

                                        <b-input-group-append>
                                            <submit-button
                                                :submit="() => submitProp('setup_script')"
                                                ref="setupScriptBtn"/>
                                        </b-input-group-append>
                                    </b-input-group>
                                </template>

                                <div v-else>
                                    <code>{{ test.setup_script }}</code>

                                    <template v-if="result && canViewAutoTest">
                                        <b-tabs no-fade>
                                            <b-tab title="stdout">
                                                <inner-code-viewer class="rounded border"
                                                                   :assignment="assignment"
                                                                   :code-lines="prepareOutput(result.setupStdout)"
                                                                   :file-id="-1"
                                                                   :feedback="{}"
                                                                   :start-line="0"
                                                                   :show-whitespace="true"
                                                                   :warn-no-newline="false"
                                                                   :empty-file-message="'No output.'" />
                                            </b-tab>

                                            <b-tab title="stderr">
                                                <inner-code-viewer class="rounded border"
                                                                   :assignment="assignment"
                                                                   :code-lines="prepareOutput(result.setupStdout)"
                                                                   :file-id="-1"
                                                                   :feedback="{}"
                                                                   :start-line="0"
                                                                   :show-whitespace="true"
                                                                   :warn-no-newline="false"
                                                                   :empty-file-message="'No output.'" />
                                            </b-tab>
                                        </b-tabs>
                                    </template>
                                </div>
                            </b-form-fieldset>
                        </b-card-body>
                    </collapse>
                </b-card>

                <h5 v-if="singleResult" class="my-3">
                    Categories
                </h5>

                <transition-group name="level-list">
                    <auto-test-set v-for="set, i in test.sets"
                                   v-if="!set.deleted"
                                   :class="{ 'mb-3': !result }"
                                   :key="set.id"
                                   :value="set"
                                   :assignment="assignment"
                                   :editable="configEditable"
                                   :result="result"
                                   :other-suites="allNonDeletedSuites" />
                    <p class="text-muted font-italic mb-3"
                       key="no-sets"
                       v-if="test.sets.filter(s => !s.deleted).length === 0">
                        You have not created any levels yet. Click the button below to create one.
                    </p>

                </transition-group>

                <b-button-toolbar v-if="configEditable"
                    class="justify-content-end">
                    <submit-button :submit="addSet"
                                label="Add level" />
                </b-button-toolbar>
            </b-card-body>
        </collapse>
    </b-card>

    <b-modal v-if="currentResult"
             :id="resultsModalId"
             hide-footer
             @hidden="currentResult = null"
             class="result-modal">
        <template slot="modal-title">
            {{ $utils.nameOfUser(resultSubmission.user) }} -
            {{ currentResult.pointsAchieved }} / {{ test.pointsPossible }} points
        </template>

        <auto-test :assignment="assignment"
                   :submission-id="currentResult.submissionId"
                   show-rubric
                   no-poll-run />
    </b-modal>

    <b-modal v-if="currentFixture"
             :id="fixtureModalId"
             @hidden="currentFixture = null"
             class="fixture-modal">
        <template slot="modal-title">
            Contents of fixture
            <code>$FIXTURES/{{ currentFixture.name }}</code>
        </template>

        <loader v-if="currentFixture.raw_data == null" class="my-3" />

        <template v-else>
            <b-alert v-if="currentFixture.err" show variant="danger" class="mt-3 mx-3">
                {{ currentFixture.err }}
            </b-alert>

            <inner-code-viewer v-else
                               :assignment="assignment"
                               :code-lines="prepareOutput(currentFixture.data)"
                               :file-id="-1"
                               :feedback="{}"
                               :start-line="0"
                               :show-whitespace="true"
                               :warn-no-newline="false" />
        </template>

        <b-button-toolbar slot="modal-footer">
            <div v-b-popover.hover.top="currentFixture.raw_data ? '' : 'Could not load fixture.'">
                <b-button :disabled="currentFixture.raw_data == null"
                          variant="primary"
                          @click="downloadFixture">
                    Download
                </b-button>
            </div>
        </b-button-toolbar>
    </b-modal>

    <rubric-viewer v-if="singleResult && showRubric"
                   class="mx-3 mb-3"
                   :assignment="assignment"
                   :submission="resultSubmission" />
</div>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';

import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/times';
import 'vue-awesome/icons/eye';
import 'vue-awesome/icons/eye-slash';
import 'vue-awesome/icons/chevron-down';
import 'vue-awesome/icons/exclamation-triangle';
import 'vue-awesome/icons/circle-o-notch';
import 'vue-awesome/icons/clock-o';
import 'vue-awesome/icons/check';

import decodeBuffer from '@/utils/decode';
import { visualizeWhitespace } from '@/utils/visualize';

import Collapse from './Collapse';
import AutoTestRun from './AutoTestRun';
import AutoTestSet from './AutoTestSet';
import AutoTestState from './AutoTestState';
import SubmitButton from './SubmitButton';
import MultipleFilesUploader from './MultipleFilesUploader';
import RubricViewer from './RubricViewer';
import Loader from './Loader';
import InnerCodeViewer from './InnerCodeViewer';
import DescriptionPopover from './DescriptionPopover';

export default {
    name: 'auto-test',

    props: {
        assignment: {
            type: Object,
            required: true,
        },

        editable: {
            type: Boolean,
            default: false,
        },

        submissionId: {
            type: Number,
            default: null,
        },

        showRubric: {
            type: Boolean,
            default: false,
        },

        noPollRun: {
            type: Boolean,
            default: false,
        },
    },

    data() {
        const id = this.$utils.getUniqueId();
        const singleResult = this.submissionId != null;
        const autoTestId = this.assignment.auto_test_id;

        return {
            newFixtures: [],
            internalTest: {},
            loading: true,
            message: null,
            currentFixture: null,
            currentResult: null,
            pollingInterval: 5000,
            pollingTimer: null,

            showCreateButton: !autoTestId,
            configCollapsed: autoTestId && !singleResult,
            setupCollapsed: singleResult,

            fixtureUploadId: `auto-test-base-upload-${id}`,
            fixtureModalId: `auto-test-fixture-modal-${id}`,
            preStartScriptId: `auto-test-base-pre-start-script-${id}`,
            globalPreStartScriptId: `auto-test-global-pre-start-script-${id}`,
            resultsModalId: `auto-test-results-modal-${id}`,
            gradeCalculationId: `auto-test-grade-mode-${id}`,

            gradeCalculationOptions: [
                { text: 'Minimum percentage needed to reach item', value: 'partial' },
                { text: 'Maximum percentage needed to reach item', value: 'full' },
            ],
        };
    },

    destroyed() {
        clearTimeout(this.pollingTimer);
    },

    watch: {
        assignmentId: {
            immediate: true,
            handler() {
                if (this.autoTestId == null) {
                    this.loading = false;
                    return;
                }

                this.loading = true;
                this.loadAutoTest().then(() => {
                    this.loading = false;
                });
            },
        },

        test: {
            immediate: true,
            handler() {
                if (this.test == null) {
                    this.internalTest = {};
                } else {
                    this.internalTest = {
                        grade_calculation: this.test.grade_calculation,
                        setup_script: this.test.setup_script,
                        run_setup_script: this.test.run_setup_script,
                        set_stop_points: this.test.sets.reduce(
                            (acc, set) => Object.assign(acc, { [set.id]: set.stop_points }),
                            {},
                        ),
                    };
                }
            },
        },
    },

    methods: {
        ...mapActions('courses', {
            storeForceLoadSubmissions: 'forceLoadSubmissions',
            storeLoadSubmissions: 'loadSubmissions',
        }),

        ...mapActions('autotest', {
            storeCreateAutoTest: 'createAutoTest',
            storeDeleteAutoTest: 'deleteAutoTest',
            storeUpdateAutoTest: 'updateAutoTest',
            storeLoadAutoTest: 'loadAutoTest',
            storeCreateAutoTestRun: 'createAutoTestRun',
            storeLoadAutoTestRun: 'loadAutoTestRun',
            storeCreateFixtures: 'createFixtures',
            storeToggleFixture: 'toggleFixture',
            storeLoadAutoTestResult: 'loadAutoTestResult',
            storeCreateAutoTestSet: 'createAutoTestSet',
            storeDeleteAutoTestResults: 'deleteAutoTestResults',
        }),

        ...mapActions('rubrics', {
            storeLoadRubric: 'loadRubric',
            storeLoadRubricResult: 'loadResult',
        }),

        runAutoTest() {
            return this.storeCreateAutoTestRun({
                autoTestId: this.autoTestId,
            });
        },

        afterRunAutoTest() {
            this.storeForceLoadSubmissions(this.assignmentId);
            this.configCollapsed = true;
            this.pollingTimer = setTimeout(this.loadAutoTestRun, this.pollingInterval);
        },

        loadAutoTest() {
            const promises = [this.storeLoadSubmissions(this.assignmentId)];

            if (!this.canViewAutoTest) {
                this.message = {
                    text: 'You do not have permission to view the autotest before the deadline.',
                    isError: false,
                };
            } else {
                promises.push(
                    this.storeLoadAutoTest({
                        autoTestId: this.autoTestId,
                    }).then(
                        () => {
                            this.message = null;
                            this.configCollapsed = !!this.autoTestRun && !this.singleResult;
                            return this.singleResult
                                ? this.loadSingleResult()
                                : this.loadAutoTestRun();
                        },
                        err => {
                            this.message = {
                                text: `Could not load AutoTest: ${this.$utils.getErrorMessage(
                                    err,
                                )}`,
                                isError: true,
                            };
                        },
                    ),
                );
            }

            return Promise.all(promises);
        },

        loadAutoTestRun() {
            if (!this.autoTestRun || this.autoTestRun.finished) {
                return null;
            }

            return this.storeLoadAutoTestRun({
                autoTestId: this.autoTestId,
            }).then(
                () => {
                    if (this.autoTestRun.finished) {
                        this.storeForceLoadSubmissions(this.assignment.id);
                    } else {
                        this.pollingTimer = setTimeout(this.loadAutoTestRun, this.pollingInterval);
                    }
                },
                err => {
                    switch (this.$utils.getProps(err, 500, 'response', 'status')) {
                        case 404:
                            if (this.autoTestRun) {
                                this.storeDeleteAutoTestResults({
                                    autoTestId: this.autoTestId,
                                    runId: this.autoTestRun.id,
                                    force: true,
                                }).then(c => c());
                            }
                            break;
                        case 500:
                            this.pollingInterval = setTimeout(
                                this.loadAutoTestRun,
                                this.pollingInterval,
                            );
                            break;
                        default:
                            break;
                    }
                },
            );
        },

        loadSingleResult() {
            if (!this.singleResult) {
                return null;
            }

            const promises = [
                this.loadRubric(),
                this.storeLoadAutoTestResult({
                    autoTestId: this.autoTestId,
                    submissionId: this.submissionId,
                }),
            ];

            // Poll this result until it's finished, then poll the run so we can get the
            // rubric when it is finished.
            if (this.result && this.result.finished && !this.noPollRun) {
                promises.push(
                    this.storeLoadAutoTestRun({
                        autoTestId: this.autoTestId,
                    }),
                );
            }

            return Promise.all(promises).then(
                () => {
                    this.message = null;

                    if (this.autoTestRun.finished) {
                        return this.loadRubric(true);
                    } else {
                        this.pollingTimer = setTimeout(this.loadSingleResult, this.pollingInterval);
                    }

                    return null;
                },
                err => {
                    this.message = {
                        text: this.$utils.getErrorMessage(err),
                        isError: false,
                    };
                },
            );
        },

        loadRubric(force = false) {
            return Promise.all([
                this.storeLoadRubric({
                    assignmentId: this.assignmentId,
                }),
                this.storeLoadRubricResult({
                    submissionId: this.submissionId,
                    force,
                }),
            ]);
        },

        submitProp(prop) {
            return this.storeUpdateAutoTest({
                autoTestId: this.autoTestId,
                autoTestProps: { [prop]: this.internalTest[prop] },
            });
        },

        addFixtures() {
            if (this.singleResult) {
                throw new Error('Cannot add fixtures in single result mode.');
            }

            const data = new FormData();

            this.newFixtures.forEach((f, i) => {
                data.append(`fixture_${i}`, f);
            });

            data.append(
                'json',
                new Blob([JSON.stringify({ has_new_fixtures: true })], {
                    type: 'application/json',
                }),
            );

            return this.storeCreateFixtures({
                autoTestId: this.autoTestId,
                fixtures: data,
            });
        },

        afterAddFixtures() {
            this.newFixtures = [];
        },

        removeFixture(index) {
            if (this.singleResult) {
                throw new Error('Cannot remove fixtures in single result mode.');
            }

            return this.storeUpdateAutoTest({
                autoTestId: this.autoTestId,
                autoTestProps: {
                    fixtures: this.test.fixtures.filter((_, i) => i !== index),
                },
            });
        },

        toggleHidden(index) {
            if (this.singleResult) {
                throw new Error('Cannot toggle fixtures in single result mode.');
            }

            return this.storeToggleFixture({
                autoTestId: this.autoTestId,
                fixture: this.test.fixtures[index],
            });
        },

        async openFixture(fixture) {
            if (fixture.hidden && !this.permissions.can_view_hidden_fixtures) {
                throw new Error('You do not have permission to view the contents of this fixture.');
            }

            this.currentFixture = Object.assign({}, fixture);

            await this.$nextTick();
            this.$root.$emit('bv::show::modal', this.fixtureModalId);

            this.$http
                .get(`/api/v1/auto_tests/${this.autoTestId}/fixtures/${fixture.id}`, {
                    responseType: 'arraybuffer',
                })
                .then(
                    ({ data }) => {
                        this.currentFixture = Object.assign({}, this.currentFixture, {
                            raw_data: data,
                        });
                        // May throw, so perform after storing raw_data, so the user can still
                        // download a file, even if it cannot be decoded.
                        this.currentFixture = Object.assign({}, this.currentFixture, {
                            data: decodeBuffer(data),
                        });
                    },
                    err => {
                        this.currentFixture = Object.assign({}, this.currentFixture, {
                            raw_data: null,
                            err: `Could not load fixture: ${this.$utils.getErrorMessage(err)}`,
                        });
                    },
                )
                .catch(() => {
                    this.currentFixture = Object.assign({}, this.currentFixture, {
                        err:
                            'Could not decode file. You can still download the file to view it locally.',
                    });
                });
        },

        downloadFixture() {
            this.$utils.downloadFile(
                this.currentFixture.raw_data,
                this.currentFixture.name,
                'application/octet-stream',
            );
        },

        createAutoTest() {
            if (this.singleResult) {
                throw new Error('AutoTest cannot be created on a single result page.');
            }

            return this.storeCreateAutoTest(this.assignment.id);
        },

        async afterCreateAutoTest() {
            await this.$nextTick();
            this.showCreateButton = false;
            this.configCollapsed = false;
        },

        deleteAutoTest() {
            if (this.singleResult) {
                throw new Error('AutoTest cannot be deleted on a single result page.');
            }

            return this.storeDeleteAutoTest(this.autoTestId);
        },

        async afterDeleteAutoTest() {
            await this.$nextTick();
            this.showCreateButton = true;
            this.configCollapsed = false;
        },

        canViewFixture(fixture) {
            return (
                this.permissions.can_view_autotest_fixture &&
                (!fixture.hidden || this.permissions.can_view_hidden_fixtures)
            );
        },

        addSet() {
            return this.storeCreateAutoTestSet({
                autoTestId: this.autoTestId,
            });
        },

        async openResult(result) {
            this.currentResult = result;

            await this.$nextTick();
            this.$root.$emit('bv::show::modal', this.resultsModalId);
        },

        afterDeleteResults() {
            clearTimeout(this.pollingTimer);
            this.configCollapsed = false;
        },

        prepareOutput(output) {
            const lines = (output || '').split('\n');
            return lines.map(this.$utils.htmlEscape).map(visualizeWhitespace);
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

        assignmentId() {
            return this.assignment.id;
        },

        autoTestId() {
            return this.assignment.auto_test_id;
        },

        autoTestRun() {
            const runs = this.test && this.test.runs;
            return runs && runs[0];
        },

        allNonDeletedSuites() {
            return this.test.sets.reduce((res, set) => {
                if (!set.deleted) {
                    res.push(...set.suites.filter(s => !s.deleted));
                }
                return res;
            }, []);
        },

        configEditable() {
            return this.permissions.can_edit_autotest && this.editable && !this.autoTestRun;
        },

        singleResult() {
            return this.submissionId != null;
        },

        test() {
            const id = this.autoTestId;
            return id && this.storeTests[id];
        },

        result() {
            if (!this.autoTestRun || this.submissionId == null) {
                return null;
            }
            return this.test.runs[0].results.find(r => r.submissionId === this.submissionId);
        },

        testSuites() {
            if (!this.test) return [];

            return this.test.sets.reduce((acc, set) => {
                acc.push(...set.suites);
                return acc;
            }, []);
        },

        createAutoTestPopover() {
            if (!this.permissions.can_edit_autotest) {
                return 'You do not have permission to create an AutoTest configuration.';
            } else if (this.assignment.rubric == null) {
                return 'You cannot create an AutoTest for this assignment because it does not have a rubric.';
            } else {
                return '';
            }
        },

        deleteAutoTestPopover() {
            if (!this.permissions.can_edit_autotest) {
                return 'You do not have permission to delete the AutoTest configuration.';
            } else if (!this.configEditable) {
                return 'The AutoTest cannot be deleted because there are results associated with it.';
            } else {
                return '';
            }
        },

        runAutoTestPopover() {
            let msg = 'The AutoTest cannot be run because ';

            if (!this.permissions.can_run_autotest) {
                msg += 'you do not have permission to start an AutoTest.';
            } else if (this.autoTestRun) {
                msg += 'there are already results.';
            } else if (this.test && this.test.grade_calculation == null) {
                msg += 'no rubric calculation mode has been selected.';
            } else if (this.testSuites.length === 0) {
                msg += 'it has no test categories.';
            } else if (this.testSuites.some(s => s.steps.length === 0)) {
                msg += 'some categories have no steps.';
            } else if (
                this.testSuites.some(s => s.steps.reduce((acc, st) => acc + st.weight, 0) <= 0)
            ) {
                msg += 'some categories have a maximum of 0 points that can be achieved.';
            } else {
                return '';
            }

            return msg;
        },

        hasEnvironmentSetup() {
            return (
                this.test != null &&
                (this.test.fixtures.length || this.test.setup_script || this.test.run_setup_script)
            );
        },

        assignmentDone() {
            return this.assignment.state === 'done';
        },

        canViewAutoTest() {
            return this.permissions.can_view_autotest_before_done || this.assignmentDone;
        },

        canCreateAutoTest() {
            return this.permissions.can_edit_autotest && this.assignment.rubric == null;
        },

        canRunAutoTest() {
            return this.permissions.can_run_autotest && !this.autoTestRun;
        },

        canDeleteAutoTest() {
            return this.permissions.can_edit_autotest && !this.autoTestRun;
        },

        canViewFixtures() {
            return this.permissions.can_view_autotest_fixture && this.test.fixtures.length;
        },

        isConfigCollapsible() {
            return this.autoTestId && this.autoTestRun;
        },

        resultSubmission() {
            const submissionId = this.submissionId || this.currentResult.submissionId;

            if (submissionId == null) {
                return null;
            }

            return this.assignment.submissions.find(s => s.id === submissionId);
        },
    },

    components: {
        Collapse,
        Icon,
        AutoTestRun,
        AutoTestSet,
        AutoTestState,
        SubmitButton,
        MultipleFilesUploader,
        RubricViewer,
        Loader,
        InnerCodeViewer,
        DescriptionPopover,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.auto-test-runs-enter-active,
.auto-test-runs-leave-active {
    transition-property: max-height margin;
    transition-duration: 750ms;
    overflow: hidden;
}

.auto-test-runs-enter,
.auto-test-runs-leave-to {
    max-height: 0;
    margin: 0 !important;
}

.auto-test-runs-enter-to,
.auto-test-runs-leave {
    max-height: 100vh;
}

.fixture-list {
    min-height: 2.5rem;
    max-height: 15rem;
    overflow: auto;

    > :last-child {
        border-bottom: 0 !important;
    }
}

.fixture-list-enter-active,
.fixture-list-leave-active {
    transition-property: max-height;
    transition-duration: @transition-duration;
    overflow: hidden;
}

.fixture-list-enter,
.fixture-list-leave-to {
    max-height: 0;
}

.fixture-list-enter-to,
.fixture-list-leave {
    max-height: 3rem;
}

.level-list-enter-active,
.level-list-leave-active {
    transition-property: max-height margin;
    transition-duration: 2 * @transition-duration;
    overflow: hidden;
}

.level-list-enter,
.level-list-leave-to {
    max-height: 0;
    margin: 0 !important;
}

.level-list-enter-to,
.level-list-leave {
    max-height: 10rem;
}

.setup-env-wrapper {
    fieldset {
        &:last-child {
            margin-bottom: 0;
        }
    }

    .inner-code-viewer {
        border-top-width: 0 !important;
        border-top-left-radius: 0 !important;
        border-top-right-radius: 0 !important;
    }
}

.upload-fixtures-wrapper {
    overflow: hidden;
}
</style>

<style lang="less">
@import '~mixins.less';

.auto-test {
    .fixture-modal,
    .result-modal {
        .modal-dialog {
            max-width: calc(100vw - 8rem);
            width: calc(100vw - 8rem);
            margin-top: 2rem;
        }

        .modal-body {
            padding: 0;
        }
    }

    .custom-control.readably-disabled label,
    .readably-disabled .custom-control label {
        opacity: 1 !important;
        color: @text-color;

        #app.dark & {
            color: @text-color-dark;
        }
    }

    .custom-radio {
        padding: 0.25rem 2.25rem;

        &:not(:last-child) {
            border-bottom: 1px solid rgba(0, 0, 0, 0.125);
        }

        label::before,
        label::after {
            margin-top: 0.25rem;
            margin-left: 0.75rem;
        }
    }

    .toggle .fa-icon,
    .toggle.fa-icon {
        margin-right: 0.5rem;
        transition: transform @transition-duration;
    }

    .x-collapsing > .handle,
    .x-collapsed > .handle {
        .toggle .fa-icon,
        .toggle.fa-icon {
            transform: rotate(-90deg);
        }
    }
}
</style>
