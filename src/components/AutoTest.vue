<template>
<b-alert v-if="error"
         show
         variant="danger"
         class="error-message">
    {{ error }}
</b-alert>

<loader v-else-if="loading" />

<div v-else class="auto-test" :class="{ editable, 'config-editable': configEditable, 'no-card': noCard }">
    <template v-if="hasResults && !singleResult">
        <b-card no-body v-for="run in test.runs" :key="run.id" class="results-card">
            <b-card-header class="auto-test-header" :class="{ editable }">
                <div class="toggle" :key="resultsCollapseId" v-b-toggle="resultsCollapseId">
                    <icon class="expander" name="chevron-right" :scale="0.75" />
                    Results
                </div>


                <div v-if="editable" class="btn-wrapper">

                <div class="btn btn-secondary" style="pointer-events: none;">
                    <auto-test-state :state="run.state" />
                    {{ capitalize(run.state.replace(/_/g, ' ')) }}
                </div>
                    <submit-button
                        :submit="() => deleteResults(run.id)"
                        variant="danger"
                        confirm="Are you sure you want to delete the results?"
                        label="Delete"/>
                </div>
            </b-card-header>

            <b-collapse :id="resultsCollapseId" visible>
                <table class="table table-striped results-table"
                        :class="{ 'table-hover': run.results.length > 0 }">
                    <thead>
                        <tr>
                            <th class="name">Name</th>
                            <th class="score">Score</th>
                            <th class="state">State</th>
                        </tr>
                    </thead>

                    <tbody>
                        <template v-if="run.results.length > 0">
                            <tr v-for="result in run.results"
                                :key="result.submission.user.id"
                                @click="openResult(result)">
                                <td class="name">{{ nameOfUser(result.submission.user) }}</td>
                                <td class="score">
                                    <icon v-if="result.submission.grade_overridden"
                                          v-b-popover.top.hover="'This submission\'s calculated grade has been manually overridden'"
                                          name="exclamation-triangle"/>
                                    {{ getProps(result.pointsAchieved, '-') }} / {{ test.pointsPossible }}
                                </td>
                                <td class="state">
                                    <auto-test-state :state="result.state" />
                                </td>
                            </tr>
                        </template>
                        <template v-else>
                            <tr>
                                <td colspan="3">No results</td>
                            </tr>
                        </template>
                    </tbody>
                </table>
            </b-collapse>
        </b-card>
    </template>

    <b-card no-body>
        <template v-if="!noCard">
            <b-card-header v-if="editable" class="auto-test-header editable">
                <span class="toggle" :key="configCollapseId" v-b-toggle="configCollapseId">
                    <icon class="expander" name="chevron-right" :scale="0.75" />
                    Configuration
                </span>
                <div class="btn-wrapper"
                    v-b-popover.hover.top="!configEditable ? 'The AutoTest configuration cannot be deleted because there are results associated with it.' : ''">
                    <submit-button
                        v-if="!loading && test == null"
                        label="Create AutoTest"
                        key="create-btn"
                        :submit="createAutoTest"
                        @success="afterCreateAutoTest"/>
                    <submit-button
                        v-if="!loading && test != null"
                        label="Run"
                        :submit="runAutoTest" />
                    <submit-button
                        v-if="!loading && test != null"
                        :submit="deleteAutoTest"
                        key="delete-btn"
                        @after-success="afterDeleteAutoTest"
                        variant="danger"
                        confirm="Are you sure you want to delete this AutoTest configuration?"
                        label="Delete"
                        :disabled="!configEditable"/>
                </div>
            </b-card-header>
            <b-card-header v-else class="auto-test-header">
                AutoTest
            </b-card-header>
        </template>

        <b-card-body v-if="test == null" key="empty">
            <div class="text-muted">You have no AutoTest yet for this assignment</div>
        </b-card-body>
        <b-collapse v-else :id="configCollapseId" :visible="singleResult || !hasResults">
            <b-card-body key="full">
                <b-card no-body>
                    <span
                        slot="header"
                        class="setup-env-wrapper-header"
                        v-if="singleResult"
                        v-b-toggle="autoTestSetupEnvWrapperId">
                        <icon v-if="singleResult" name="chevron-right" :scale="0.75" />
                        Environment setup
                    </span>
                    <template v-else slot="header">Environment setup</template>

                    <b-collapse
                        :id="autoTestSetupEnvWrapperId"
                        :visible="!singleResult">
                        <b-card-body>
                            <b-form-fieldset>
                                <label :for="baseSystemId">Base systems</label>

                                <b-input-group v-if="configEditable">
                                    <multiselect
                                        :close-on-select="false"
                                        :id="baseSystemId"
                                        class="base-system-selector"
                                        v-model="internalTest.base_systems"
                                        :options="baseSystems"
                                        :searchable="true"
                                        :custom-label="a => a.name"
                                        multiple
                                        track-by="id"
                                        label="label"
                                        :hide-selected="false"
                                        placeholder="Select base systems"
                                        :internal-search="true"
                                        :loading="false">
                                        <span slot="noResult" class="text-muted">
                                            No results were found.
                                        </span>
                                    </multiselect>
                                    <b-input-group-append>
                                        <submit-button :submit="() => submitProp('base_systems')" />
                                    </b-input-group-append>
                                </b-input-group>
                                <div v-else class="multiselect">
                                    <div class="multiselect__tags">
                                        <div class="multiselect__tags-wrap">
                                            <span v-for="base in test.base_systems"
                                                  class="multiselect__tag no-close">
                                                {{ base.name }}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </b-form-fieldset>

                            <transition :name="disabledAnimations ? '' : 'fixtureswrapper'">
                                <div v-if="test.fixtures.length > 0" class="transition">
                                    <b-form-fieldset>
                                        <label :for="uploadedFixturesId">
                                            Uploaded fixtures
                                        </label>
                                        <ul class="fixture-list">
                                            <transition-group :name="disabledAnimations ? '' : 'fixtures'">
                                                <li v-for="fixture, index in test.fixtures"
                                                    class="transition fixture-row"
                                                    :key="fixture.id">
                                                    <template v-if="configEditable">
                                                        <a
                                                            class="fixture-name"
                                                            href="#"
                                                            @click="openFile(fixture, $event)">
                                                            {{ fixture.name }}
                                                        </a>

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
                                                    <template v-else>
                                                        <component
                                                            :is="canViewFixture(fixture) ? 'a' : 'span'"
                                                            class="fixture-name"
                                                            href="#">
                                                            {{ fixture.name }}
                                                        </component>

                                                        <icon
                                                            v-if="fixture.hidden"
                                                            name="eye-slash"
                                                            v-b-popover.top.hover="`This fixture is hidden. ${singleResult && !canViewFixture(fixture) ? 'You' : 'Students'} may not view its contents.`"/>
                                                    </template>
                                                </li>
                                            </transition-group>
                                        </ul>
                                    </b-form-fieldset>
                                </div>
                            </transition>

                            <b-form-fieldset class="fixture-upload-wrapper" v-if="configEditable">
                                <label :for="fixtureUploadId">
                                    Upload fixtures
                                </label>
                                <multiple-files-uploader
                                    v-model="newFixtures"
                                    :id="fixtureUploadId">
                                    Click here or drop file(s) add fixtures and test files.
                                </multiple-files-uploader>
                                <b-input-group>
                                    <b-input-group-prepend is-text
                                                            class="fixture-upload-information">
                                    </b-input-group-prepend>
                                    <b-input-group-append>
                                        <submit-button
                                            :disabled="newFixtures.length === 0"
                                            @after-success="afterAddFixtures"
                                            class="upload-fixture-btn"
                                            :submit="addFixtures" />
                                    </b-input-group-append>
                                </b-input-group>
                            </b-form-fieldset>

                            <b-form-fieldset class="setup-output-wrapper">
                                <template v-if="configEditable">
                                    <label :for="preStartScriptId">
                                        Setup script to run
                                    </label>
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
                                <template v-else-if="editable && test.setup_script">
                                    <label :for="preStartScriptId">
                                        Setup script to run: <code>{{ test.setup_script }}</code>
                                    </label>
                                </template>
                                <template v-else-if="test.setup_script">
                                    <label>
                                        Setup script output: <code>{{ test.setup_script }}</code>
                                    </label>
                                    <b-tabs no-fade v-if="result">
                                        <b-tab title="stdout">
                                            <pre v-if="result.setupStdout">{{ result.setupStdout }}</pre>
                                            <pre v-else class="text-muted">No output.</pre>
                                        </b-tab>
                                        <b-tab title="stderr">
                                            <pre v-if="result.setupStderr">{{ result.setupStderr }}</pre>
                                            <pre v-else class="text-muted">No output.</pre>
                                        </b-tab>
                                    </b-tabs>
                                </template>
                            </b-form-fieldset>
                        </b-card-body>
                    </b-collapse>
                </b-card>

                <transition :name="disabledAnimations ? '' : 'emptytext'">
                    <div class="text-muted empty-text transition"
                            v-if="test.sets.filter(s => !s.deleted).length === 0">
                        You have no test sets yet. Click the button below to create one.
                    </div>
                </transition>
                <transition-group :name="disabledAnimations ? '' : 'list'">
                    <div v-for="set, i in test.sets"
                            v-if="!set.deleted"
                            :key="set.id"
                            class="list-item transition">
                        <b-card no-body class="test-group auto-test-set">
                            <b-card-header class="test-set-header" :class="{ editable: configEditable }">
                                Test set
                                <div class="btn-wrapper" v-if="configEditable">
                                    <submit-button
                                        :submit="() => deleteSet(set)"
                                        label="Delete set"
                                        variant="outline-danger"
                                        confirm="Are you sure you want to delete this test set and
                                                    all suits in it."/>
                                </div>
                            </b-card-header>
                            <b-card-body>
                                <span class="text-muted"
                                      v-if="set.suites.filter(s => !s.isEmpty() && !s.deleted).length === 0">
                                    You have no suites yet. Click the button below to create one.
                                </span>
                                <masonry :cols="{default: (singleResult ? 1 : 2), [$root.largeWidth]: 1 }"
                                         :gutter="30"
                                         class="outer-block">
                                    <auto-test-suite v-for="suite, j in set.suites"
                                                     v-if="!suite.deleted"
                                                     :editable="configEditable"
                                                     :editing="suite.steps.length === 0"
                                                     :key="suite.id"
                                                     :assignment="assignment"
                                                     :other-suites="allNonDeletedSuites"
                                                     :value="set.suites[j]"
                                                     :result="result"
                                                     @input="updateSuite(set, j, $event)"
                                                     @delete="deleteSuite(suite)" />
                                </masonry>
                                <div v-if="configEditable"
                                     class="btn-wrapper"
                                     style="float: right;">
                                    <submit-button
                                        :submit="() => addSuite(set)"
                                        label="Add suite"/>
                                </div>
                            </b-card-body>
                            <transition :name="disabledAnimations ? '' : 'setcontinue'">
                                <b-card-footer v-if="configEditable && test.sets.some((s, j) => j > i && !s.deleted)"
                                                class="transition set-continue">
                                    Only execute other test sets when achieved grade by AutoTest is higher than
                                    <b-input-group class="input-group">
                                        <input
                                            class="form-control"
                                            type="number"
                                            v-model="internalTest.set_stop_points[set.id]"
                                            @keyup.ctrl.enter="$refs.submitContinuePointsBtn[i].onClick()"
                                            placeholder="0" />
                                        <b-input-group-append>
                                            <submit-button
                                                ref="submitContinuePointsBtn"
                                                :submit="() => submitContinuePoints(set)" />
                                        </b-input-group-append>
                                    </b-input-group>
                                </b-card-footer>
                                <b-card-footer
                                    v-else-if="result && i < test.sets.length - 1"
                                    class="set-continue">
                                    <template v-if="set.passed">
                                        Scored <code>{{ result.setResults[set.id].achieved }}</code> points,
                                        which is greater than <code>{{ set.stop_points }}</code>. Continuing
                                        with the next set.
                                    </template>
                                    <template v-else>
                                        Scored <code>{{ result.setResults[set.id].achieved }}</code> points,
                                        which is less than <code>{{ set.stop_points }}</code>. No further
                                        tests will be run.
                                    </template>
                                </b-card-footer>
                            </transition>
                        </b-card>
                    </div>
                </transition-group>
                <div v-if="configEditable"
                     class="add-btn-wrapper transition">
                    <submit-button :submit="addSet"
                                   label="Add set"
                                   class="transition"/>
            </div>

            <div slot="footer">
                <b-button-toolbar justify>
                </b-button-toolbar>
            </div>
            </b-card-body>
        </b-collapse>
    </b-card>

    <b-modal
        v-if="!singleResult && currentResult"
        :id="resultsModalId"
        hide-footer
        @hidden="currentResult = null"
        class="result-modal">
        <template slot="modal-title">
            {{ nameOfUser(currentResult.submission.user) }} -
            {{ currentResult.pointsAchieved }} / {{ test.pointsPossible }} points
        </template>

        <auto-test
            no-card
            :assignment="assignment"
            :submission-id="currentResult.submission.id" />

        <rubric-viewer
            :assignment="assignment"
            :submission="currentResult.submission"
            :rubric="currentResult.rubric" />
    </b-modal>
</div>
</template>

<script>
import Multiselect from 'vue-multiselect';

import { mapActions, mapGetters } from 'vuex';

import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/times';
import 'vue-awesome/icons/eye';
import 'vue-awesome/icons/eye-slash';
import 'vue-awesome/icons/chevron-right';
import 'vue-awesome/icons/exclamation-triangle';
import 'vue-awesome/icons/circle-o-notch';
import 'vue-awesome/icons/clock-o';
import 'vue-awesome/icons/check';

import { deepCopy, getErrorMessage, getProps, nameOfUser, getUniqueId, capitalize } from '@/utils';

import AutoTestSuite from './AutoTestSuite';
import AutoTestState from './AutoTestState';
import SubmitButton from './SubmitButton';
import MultipleFilesUploader from './MultipleFilesUploader';
import Loader from './Loader';
import RubricViewer from './RubricViewer';

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

        noCard: {
            type: Boolean,
            default: false,
        },
    },

    data() {
        const id = getUniqueId();

        return {
            getProps,
            nameOfUser,
            capitalize,

            disabledAnimations: true,
            newFixtures: [],
            internalTest: {},
            loading: true,
            error: '',
            permissions: {},
            currentResult: null,
            pollingInterval: 3000,
            pollingTimer: null,

            configCollapseId: `auto-test-config-collapse-${id}`,
            resultsCollapseId: `auto-test-results-collapse-${id}`,
            resultsModalId: `auto-test-results-modal-${id}`,
            baseSystemId: `auto-test-base-system-${id}`,
            fixtureUploadId: `auto-test-base-upload-${id}`,
            uploadedFixturesId: `auto-test-base-fixtures-${id}`,
            preStartScriptId: `auto-test-base-pre-start-script-${id}`,
            autoTestSetupEnvWrapperId: `auto-test-setup-env-${id}`,
        };
    },

    mounted() {
        this.disabledAnimations = false;
    },

    destroyed() {
        clearTimeout(this.pollingTimer);
    },

    watch: {
        assignmentId: {
            immediate: true,
            handler() {
                if (this.assignment.auto_test_id == null) {
                    this.loading = false;
                    return;
                }

                this.loading = true;

                Promise.all([
                    this.loadAutoTest(),
                    this.loadPermissions(),
                ]).then(() => {
                    this.loading = false;
                }, () => {
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
                        base_systems: this.test.base_systems,
                        setup_script: this.test.setup_script,
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
        ...mapActions('courses', ['updateAssignment']),

        ...mapActions('autotest', {
            storeCreateAutoTest: 'createAutoTest',
            storeDeleteAutoTest: 'deleteAutoTest',
            storeUpdateAutoTest: 'updateAutoTest',
            storeLoadAutoTest: 'loadAutoTest',
            storeCreateAutoTestRun: 'createAutoTestRun',
            storeLoadAutoTestRun: 'loadAutoTestRun',
            storeCreateFixtures: 'createFixtures',
            storeToggleFixture: 'toggleFixture',
            storeCreateAutoTestSet: 'createAutoTestSet',
            storeDeleteAutoTestSet: 'deleteAutoTestSet',
            storeUpdateAutoTestSet: 'updateAutoTestSet',
            storeCreateAutoTestSuite: 'createAutoTestSuite',
            storeDeleteAutoTestSuite: 'deleteAutoTestSuite',
            storeUpdateAutoTestSuite: 'updateAutoTestSuite',
            storeLoadAutoTestResult: 'loadAutoTestResult',
            storeDeleteAutoTestResults: 'deleteAutoTestResults',
        }),

        runAutoTest() {
            this.storeCreateAutoTestRun({
                autoTestId: this.assignment.auto_test_id,
            }).then(
                () => this.loadAutoTestRun(),
            );
        },

        loadAutoTest() {
            return this.storeLoadAutoTest({
                autoTestId: this.assignment.auto_test_id,
            }).then(
                () => {
                    this.loadAutoTestRun();
                    return this.loadSingleResult();
                },
                err => {
                    this.error = `Could not load AutoTest: ${getErrorMessage(err)}`;
                },
            );
        },

        loadAutoTestRun() {
            if (!this.hasResults || this.singleResult || this.test.runs[0].finished) {
                return;
            }

            this.pollingTimer = setTimeout(() => {
                this.storeLoadAutoTestRun({
                    autoTestId: this.assignment.auto_test_id,
                }).then(
                    () => this.loadAutoTestRun(),
                    err => {
                        this.error = `Could not load AutoTest: ${getErrorMessage(err)}`;
                    },
                );
            }, this.pollingInterval);
        },

        loadSingleResult() {
            if (!this.singleResult) {
                return null;
            }

            return Promise.all([
                this.storeLoadAutoTestResult({
                    autoTestId: this.assignment.auto_test_id,
                    submissionId: this.submissionId,
                }),
            ]).then(
                () => {
                    if (!this.result.finished) {
                        this.pollingTimer = setTimeout(this.loadSingleResult, this.pollingInterval);
                    }
                },
                err => {
                    this.error = `Could not load AutoTest result: ${getErrorMessage(err)}`;
                },
            );
        },

        loadPermissions() {
            const names = ['can_view_hidden_fixtures'];

            return this.$hasPermission(names, this.assignment.course.id).then(perms => {
                perms.forEach((value, i) => {
                    this.permissions[names[i]] = value;
                });
            });
        },

        openFile(_, event) {
            event.preventDefault();
        },

        addSet() {
            return this.storeCreateAutoTestSet({
                autoTestId: this.test.id,
            });
        },

        deleteSet(set) {
            return this.storeDeleteAutoTestSet({
                autoTestId: this.test.id,
                setId: set.id,
            });
        },

        submitContinuePoints(set) {
            const stopPoints = Number(this.internalTest.set_stop_points[set.id]);
            return this.storeUpdateAutoTestSet({
                autoTestId: this.test.id,
                autoTestSet: set,
                setProps: { stop_points: stopPoints },
            });
        },

        addSuite(set) {
            return this.storeCreateAutoTestSuite({
                autoTestId: this.test.id,
                autoTestSet: set,
            });
        },

        updateSuite(set, index, suite) {
            return this.storeUpdateAutoTestSuite({
                autoTestSet: set,
                index,
                suite,
            });
        },

        deleteSuite(suite) {
            return this.storeDeleteAutoTestSuite({
                autoTestSuite: suite,
            });
        },

        submitProp(prop) {
            return this.storeUpdateAutoTest({
                autoTestId: this.test.id,
                autoTestProps: { [prop]: this.internalTest[prop] },
            });
        },

        addFixtures() {
            const data = new FormData();

            this.newFixtures.forEach((f, i) => {
                data.append(`fixture_${i}`, f);
            });

            data.append(
                'json',
                new Blob(
                    [
                        JSON.stringify({
                            has_new_fixtures: true,
                        }),
                    ],
                    {
                        type: 'application/json',
                    },
                ),
            );

            return this.storeCreateFixtures({
                autoTestId: this.test.id,
                fixtures: data,
            });
        },

        afterAddFixtures() {
            this.newFixtures = [];
        },

        removeFixture(index) {
            this.storeUpdateAutoTest({
                autoTestId: this.test.id,
                autoTestProps: {
                    fixtures: this.test.fixtures.filter((_, i) => i !== index),
                },
            });
        },

        toggleHidden(index) {
            return this.storeToggleFixture({
                autoTestId: this.test.id,
                fixture: this.test.fixtures[index],
            });
        },

        createAutoTest() {
            this.disabledAnimations = true;
            return this.storeCreateAutoTest(this.assignment.id);
        },

        async afterCreateAutoTest() {
            await this.$nextTick();
            this.disabledAnimations = false;
        },

        deleteAutoTest() {
            this.disabledAnimations = true;
            return this.storeDeleteAutoTest(this.test.id);
        },

        async afterDeleteAutoTest() {
            await this.$nextTick();
            this.disabledAnimations = false;
        },

        deleteResults(id) {
            return this.storeDeleteAutoTestResults({
                autoTestId: this.test.id,
                runId: id,
            });
        },

        async openResult(result) {
            if (result.state === 'not_started') {
                return;
            }

            const { data: rubric } = await this.$http.get(
                `/api/v1/submissions/${result.submission.id}/rubrics/`,
            );

            this.currentResult = Object.assign({}, result, {
                rubric: Object.assign(rubric, {
                    rubrics: deepCopy(this.assignment.rubric),
                }),
            });

            await this.$nextTick();
            this.$root.$emit('bv::show::modal', this.resultsModalId);
        },

        canViewFixture(fixture) {
            return !fixture.hidden || this.permissions.can_view_hidden_fixtures;
        },
    },

    computed: {
        ...mapGetters('autotest', {
            allTests: 'tests',
            allResults: 'results',
        }),

        assignmentId() {
            return this.assignment.id;
        },

        allNonDeletedSuites() {
            return this.test.sets.reduce((res, set) => {
                if (!set.deleted) {
                    res.push(...set.suites.filter(s => !s.deleted));
                }
                return res;
            }, []);
        },

        baseSystems() {
            const langSet = new Set();
            const selectedSet = new Set();
            this.internalTest.base_systems.forEach(t => {
                langSet.add(t.group);
                selectedSet.add(t.id);
            });

            return AutoTestBaseSystems.reduce((res, cur) => {
                if (langSet.has(cur.group) && !selectedSet.has(cur.id)) {
                    res.push({
                        ...cur,
                        $isDisabled: true,
                    });
                } else {
                    res.push(cur);
                }
                return res;
            }, []);
        },

        selectedBaseSystems() {
            return this.internalTest.base_systems;
        },

        hasResults() {
            const runs = this.test && this.test.runs;
            return !!(runs && runs.length);
        },

        configEditable() {
            return this.editable && !this.hasResults;
        },

        singleResult() {
            return this.submissionId != null;
        },

        test() {
            const id = this.assignment.auto_test_id;
            return id && this.allTests[id];
        },

        result() {
            if (!this.hasResults || this.submissionId == null) {
                return null;
            }
            return this.test.runs[0].results.find(r => r.submission.id === this.submissionId);
        },
    },

    components: {
        Icon,
        Multiselect,
        AutoTestSuite,
        AutoTestState,
        SubmitButton,
        MultipleFilesUploader,
        Loader,
        RubricViewer,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.auto-test.no-card > .card {
    border: 0;
}

.auto-test-suite:not(.empty-auto-test-suite) {
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

.transition {
    transition: all 0.3s linear;
}

.list-item {
    margin-top: 1rem;
}

.add-btn-wrapper,
.test-suites-button-wrapper {
    margin-top: 1rem;
}

.test-suites-button-wrapper,
.add-btn-wrapper {
    display: flex;
    justify-content: flex-end;
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

.setcontinue-enter-active,
.setcontinue-leave-active,
.emptytext-enter-active,
.emptytext-leave-active {
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
.setcontinue-leave-to,
.emptytext-enter,
.emptytext-leave-to {
    max-height: 0;
    overflow-y: hidden;
    margin: 0 !important;
}

.empty-text {
    margin-top: 1rem;
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

.auto-test-header,
.test-set-header {
    align-items: center;
    display: flex;
    justify-content: space-between;

    &.editable {
        padding: 5px 1.25rem;
    }

    .toggle {
        cursor: pointer;

        .fa-icon {
            margin-right: 0.5rem;
            transition: transform 300ms;
        }

        &:not(.collapsed) .fa-icon {
            transform: rotate(90deg);
        }
    }
}

.fixtureswrapper-leave-active,
.fixtureswrapper-enter-active,
.fixtures-leave-active,
.fixtures-enter-active {
    max-height: 10rem;
    overflow-y: hidden;
    opacity: 1;
}

.fixtures-enter-active {
    background-color: fade(@color-success, 50%) !important;
}

.fixtures-leave-active {
    background-color: #d9534f !important;
}

.fixtureswrapper-enter,
.fixtureswrapper-leave-to,
.fixtures-enter,
.fixtures-leave-to {
    opacity: 0;
    max-height: 0;
    overflow-y: hidden;
    border-color: transparent;
}

.fixture-name {
    flex: 1 1 auto;
}

.fixture-list {
    border-radius: 0.25rem;
    border: 1px solid @color-border-gray-lighter;
    #app.dark & {
        border-color: @color-primary-darker;
    }
    padding: 0;
    margin: 0;
    .fixture-row {
        padding: 5px 0.75rem;
        display: flex;
        align-items: center;

        &:not(:last-child) {
            border-bottom: 1px solid @color-border-gray-lighter;
        }
        #app.dark & {
            border-color: @color-primary-darker;
        }
    }
}

.fixture-upload-wrapper {
    .fixture-upload-information {
        flex: 1 1 auto;

        .input-group-text {
            border-top: none;
            border-top-left-radius: 0;
            border-top-right-radius: 0;
            width: 100%;
            background-color: transparent !important;

            #app.dark & {
                color: @text-color-dark !important;
            }
        }
    }

    .upload-fixture-btn {
        border-top-right-radius: 0;
    }
}

.results-card {
    margin-bottom: 1rem;
}

.results-table {
    margin-bottom: 0;

    th {
        border-top: 0;
    }

    .caret,
    .score,
    .state {
        width: 1px;
        white-space: nowrap;
    }

    .score {
        text-align: right;

        .fa-icon {
            transform: translateY(2px);
            margin-right: 0.5rem;
        }
    }

    .state {
        text-align: center;
    }
}

.setup-env-wrapper-header {
    cursor: pointer;

    .fa-icon {
        margin-right: 0.25rem;
        transition: transform 300ms;
    }

    &:not(.collapsed) .fa-icon {
        transform: rotate(90deg);
    }
}

.setup-output-wrapper {
    margin-bottom: 0;

    pre {
        margin-bottom: 0;
        border: 1px solid @color-border-gray-lighter;
        border-top-width: 0;
        border-bottom-left-radius: 0.25rem;
        border-bottom-right-radius: 0.25rem;
        padding: 1rem;
    }

    #app.dark & {
        pre {
            color: @text-color-dark;
            border-color: @color-primary-darker;
        }
    }
}

.error-message {
    margin: 1rem;
}

.rubric-viewer {
    margin: 0 1rem 1rem;
}
</style>

<style lang="less">
.auto-test .base-system-selector {
    flex: 1;

    .multiselect__tags {
        z-index: 10;
        border-bottom-right-radius: 0;
        border-top-right-radius: 0;
    }
}

.multiselect__tag.no-close {
    padding-right: 10px;
}

.result-modal {
    .modal-dialog {
        max-width: calc(100vw - 8rem);
        width: calc(100vw - 8rem);
        margin-top: 2rem;
    }

    .auto-test & .modal-body {
        padding: 0;
    }
}
</style>
