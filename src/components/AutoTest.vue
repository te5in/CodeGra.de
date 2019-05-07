<template>
<div class="auto-test" :class="{ editable, 'config-editable': configEditable, 'no-border': noBorder }">
    <template v-if="!singleResult && hasResults">
        <b-card no-body v-for="run in test.runs" class="results-card">
            <b-card-header class="auto-test-header" :class="{ editable }">
                <span class="toggle" :key="resultsCollapseId" v-b-toggle="resultsCollapseId">
                    <icon class="expander" name="chevron-right" :scale="0.75" />
                    Results
                </span>
                <div v-if="editable"
                        class="btn-wrapper">
                    <submit-button
                        :submit="() => deleteResults(run.id)"
                        @after-success="afterDeleteResults"
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
                                :key="result.work.user.id"
                                @click="openResult(result)">
                                <td class="name">{{ nameOfUser(result.work.user) }}</td>
                                <td class="score">
                                    <icon v-if="result.work.grade_overridden"
                                          v-b-popover.top.hover="'This submission\'s calculated grade has been manually overridden'"
                                          name="exclamation-triangle"/>
                                    {{ result.points_achieved }}
                                </td>
                                <td class="state">{{ result.state }}</td>
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
        <b-card-header v-if="editable" class="auto-test-header editable">
            <span class="toggle" :key="configCollapseId" v-b-toggle="configCollapseId">
                <icon class="expander" name="chevron-right" :scale="0.75" />
                AutoTest
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

        <b-card-body v-if="loading" key="loading">
            <loader/>
        </b-card-body>
        <b-card-body v-else-if="test == null" key="empty">
            <div class="text-muted">You have no AutoTest yet for this assignment</div>
        </b-card-body>
        <b-collapse v-else :id="configCollapseId" :visible="singleResult || !hasResults">
            <b-card-body key="full">
                <div class="setup-env-wrapper">
                    <h5>Environment setup</h5>
                    <b-form-fieldset>
                        <label :for="baseSystemId">Base systems</label>

                        <b-input-group v-if="configEditable">
                            <multiselect
                                :close-on-select="false"
                                :id="baseSystemId"
                                class="base-system-selector"
                                v-model="test.base_systems"
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
                                <submit-button :submit="submitBaseSystems" />
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
                                                        :submit="() => removeFixture(index)"
                                                        @success="removeFixtureSuccess">
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

                    <b-form-fieldset v-if="configEditable">
                        <label :for="preStartScriptId">
                            Setup script to run
                        </label>
                        <b-input-group>
                            <input class="form-control"
                                    @keydown.ctrl.enter="$refs.setupScriptBtn.onClick"
                                    :id="preStartScriptId"
                                    v-model="test.setup_script"/>
                            <b-input-group-append>
                                <submit-button :submit="submitSetupScript" ref="setupScriptBtn"/>
                            </b-input-group-append>
                        </b-input-group>
                    </b-form-fieldset>
                    <b-form-fieldset v-else-if="editable && test.setup_script">
                        <label :for="preStartScriptId">
                            Setup script to run: <code>{{ test.setup_script }}</code>
                        </label>
                    </b-form-fieldset>
                    <b-form-fieldset v-else-if="test.setup_script">
                        <label>
                            Setup script output: <code>{{ test.setup_script }}</code>
                        </label>
                        <b-tabs no-fade>
                            <b-tab title="stdout">
                                <pre v-if="singleResult" class="setup-output"><!--
                                    -->{{ result.setup_stdout }}<!--
                                --></pre>
                            </b-tab>
                            <b-tab title="stderr">
                                <pre v-if="singleResult" class="setup-output"><!--
                                    -->{{ result.setup_stderr }}<!--
                                --></pre>
                            </b-tab>
                        </b-tabs>
                    </b-form-fieldset>
                </div>

                <hr style="margin-bottom: 0;"/>

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
                        <b-card class="test-group auto-test-set"
                                no-body>
                            <b-card-header class="test-set-header" :class="{ editable: configEditable }">
                                Test set
                                <div class="btn-wrapper" v-if="configEditable">
                                    <submit-button
                                        :submit="() => deleteSet(i)"
                                        @success="afterDeleteSet"
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
                                <masonry :cols="{default: 2, [$root.largeWidth]: 1, [$root.mediumWidth]: 1 }"
                                            :gutter="30"
                                            class="outer-block">
                                    <auto-test-suite v-for="suite, j in set.suites"
                                                     v-if="!suite.deleted"
                                                     :editable="configEditable"
                                                     :editing="suite.steps.length === 0"
                                                     :key="suite.id"
                                                     :assignment="assignment"
                                                     :other-suites="allNonDeletedSuites"
                                                     @delete="$set(suite, 'deleted', true)"
                                                     v-model="set.suites[j]"
                                                     :result="result"/>
                                </masonry>
                                <div v-if="configEditable"
                                     class="btn-wrapper"
                                     style="float: right;">
                                    <submit-button
                                        :submit="() => addSuite(i)"
                                        label="Add suite"/>
                                </div>
                            </b-card-body>
                            <transition :name="disabledAnimations ? '' : 'setcontinue'">
                                <b-card-footer v-if="test.sets.some((s, j) => j > i && !s.deleted)"
                                                class="transition set-continue">
                                    Only execute other test sets when achieved grade by AutoTest is higher than
                                    <b-input-group class="input-group">
                                        <input class="form-control"
                                                type="number"
                                                v-model="set.stop_points"
                                                @keyup.ctrl.enter="$refs.submitContinuePointsBtn[i].onClick()"
                                                placeholder="0"
                                            />
                                        <b-input-group-append>
                                            <submit-button
                                                ref="submitContinuePointsBtn"
                                                :submit="() => submitContinuePoints(set)" />
                                        </b-input-group-append>
                                    </b-input-group>
                                </b-card-footer>
                            </transition>
                        </b-card>
                    </div>
                </transition-group>
                <div v-if="configEditable"
                     class="add-btn-wrapper transition">
                    <submit-button :submit="addSet"
                                    @success="afterAddSet"
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

    <b-modal :id="resultsModalId" hide-footer size="lg" @hidden="currentResult = null">
        <template v-if="currentResult" slot="modal-title">
            {{ nameOfUser(currentResult.work.user) }} - {{ currentResult.achieved_points }} points
        </template>

        <auto-test
            v-if="currentResult"
            :assignment="assignment"
            :result="currentResult"
            :test-config="test"
            :editable="false" />
    </b-modal>
</div>
</template>

<script>
import Multiselect from 'vue-multiselect';

import { mapActions } from 'vuex';

import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/times';
import 'vue-awesome/icons/eye';
import 'vue-awesome/icons/eye-slash';
import 'vue-awesome/icons/chevron-right';
import 'vue-awesome/icons/exclamation-triangle';

import { nameOfUser, getUniqueId, getProps, deepCopy, withOrdinalSuffix } from '@/utils';

import AutoTestSuite from './AutoTestSuite';
import SubmitButton from './SubmitButton';
import MultipleFilesUploader from './MultipleFilesUploader';
import Loader from './Loader';

class AutoTestSuiteData {
    constructor($http, autoTestId, autoTestSetId, serverData = {}, trackingId = getUniqueId()) {
        this.$http = $http;
        this.trackingId = trackingId;
        this.autoTestSetId = autoTestSetId;
        this.autoTestId = autoTestId;

        this.id = null;
        this.steps = [];
        this.rubricRow = {};

        this.setFromServerData(serverData);
    }

    setFromServerData(d) {
        this.id = d.id;
        this.steps = d.steps || [];
        this.rubricRow = d.rubric_row || {};
    }

    copy() {
        return new AutoTestSuiteData(
            this.$http,
            this.autoTestId,
            this.autoTestSetId,
            {
                id: this.id,
                steps: deepCopy(this.steps),
                rubric_row: this.rubricRow,
            },
            this.trackingId,
        );
    }

    isEmpty() {
        return this.steps.length === 0;
    }

    get url() {
        return `/api/v1/auto_tests/${this.autoTestId}/sets/${this.autoTestSetId}/suites/`;
    }

    save() {
        return this.$http
            .patch(this.url, {
                id: this.id == null ? undefined : this.id,
                steps: this.steps.map(step => ({
                    ...step,
                    weight: Number(step.weight),
                })),
                rubric_row_id: this.rubricRow.id,
            })
            .then(({ data }) => this.setFromServerData(data));
    }

    delete() {
        if (this.id != null) {
            return this.$http.delete(`${this.url}/${this.id}`);
        } else {
            return Promise.resolve();
        }
    }

    removeItem(index) {
        this.steps.splice(index, 1);
    }

    addStep(step) {
        this.steps.push(step);
    }

    checkValid(step) {
        const isEmpty = val => !val.match(/[a-zA-Z0-9]/);
        const errs = [];

        if (step.checkName && isEmpty(step.name)) {
            errs.push('The name may not be empty.');
        }
        if (step.checkProgram && isEmpty(step.program)) {
            errs.push('The program may not be empty.');
        }
        if (step.checkWeight && Number(step.weight) <= 0) {
            errs.push('The weight should be a number higher than 0.');
        }

        if (step.type === 'io_test') {
            if (step.data.inputs.length === 0) {
                errs.push('There should be at least one input output case.');
            } else {
                step.data.inputs.forEach((input, i) => {
                    const name = `${withOrdinalSuffix(i + 1)} input output case`;
                    if (isEmpty(input.name)) {
                        errs.push(`The name of the ${name} is emtpy.`);
                    }
                    if (Number(input.weight) <= 0) {
                        errs.push(`The weight of the ${name} should be a number higher than 0.`);
                    }
                });
            }
        } else if (step.type === 'check_points') {
            let weightBefore = 0;
            for (let i = 0; i < this.steps.length > 0; ++i) {
                if (this.steps[i].id === this.id) {
                    break;
                }
                weightBefore += Number(this.steps[i].weight);
            }
            if (step.data.min_pints <= 0 || step.data.min_points > weightBefore) {
                errs.push(
                    `The minimal amount of points should be achievable (which is ${weightBefore}) and higher than 0.`,
                );
            }
        }

        return errs;
    }

    getErrors() {
        const caseErrors = {
            general: [],
            steps: [],
            isEmpty() {
                return this.steps.length === 0 && this.general.length === 0;
            },
        };
        if (this.steps.length === 0) {
            caseErrors.general.push('You should have at least one step.');
        }

        const stepErrors = this.steps.map(s => [s, this.checkValid(s)]);
        if (stepErrors.some(([, v]) => v.length > 0)) {
            caseErrors.steps = stepErrors;
        }

        if (!this.rubricRow || !this.rubricRow.id) {
            caseErrors.general.push('You should select a rubric category for this test suite.');
        }

        return caseErrors.isEmpty() ? null : caseErrors;
    }
}

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

        result: {
            type: Object,
            default: null,
        },

        testConfig: {
            type: Object,
            default: null,
        },

        noBorder: {
            type: Boolean,
            default: false,
        },
    },

    data() {
        const id = getUniqueId();

        return {
            test: null,
            disabledAnimations: true,
            newFixtures: [],
            loading: true,
            error: '',
            permissions: {},
            currentResult: null,
            nameOfUser,

            configCollapseId: `auto-test-config-collapse-${id}`,
            resultsCollapseId: `auto-test-results-collapse-${id}`,
            resultsModalId: `auto-test-results-modal-${id}`,
            baseSystemId: `auto-test-base-system-${id}`,
            fixtureUploadId: `auto-test-base-upload-${id}`,
            uploadedFixturesId: `auto-test-base-fixtures-${id}`,
            preStartScriptId: `auto-test-base-pre-start-script-${id}`,
        };
    },

    mounted() {
        this.disabledAnimations = false;
    },

    watch: {
        assignmentId: {
            handler() {
                if (this.assignment.auto_test_id == null) {
                    this.test = null;
                    this.loading = false;
                    return;
                }

                this.loading = true;

                Promise.all([
                    this.singleResult ? this.loadSingleResult() : this.loadAutoTest(),
                    this.loadPermissions(),
                ]).then(() => {
                    this.loading = false;
                });
            },
            immediate: true,
        },
    },

    methods: {
        ...mapActions('courses', ['updateAssignment']),

        loadAutoTest() {
            return this.$http
                .get(`/api/v1/auto_tests/${this.assignment.auto_test_id}`)
                .then(
                    ({ data: test }) => {
                        test.runs = [
                            {
                                id: 1,
                                results: [
                                    {
                                        id: 1,
                                        work: {
                                            id: 1,
                                            user: { name: 'Thomas Schaper', id: 1 },
                                        },
                                        points_achieved: '-',
                                        state: 'not_started',
                                        setup_stdout: 'stdout!!!',
                                        setup_stderr: 'stderr!!!',
                                    },
                                    {
                                        id: 2,
                                        work: {
                                            id: 2,
                                            user: { name: 'Olmo Kramer', id: 2 },
                                            grade_overridden: true,
                                        },
                                        points_achieved: '12 / 13',
                                        state: 'passed',
                                        setup_stdout: 'stdout!!!',
                                        setup_stderr: 'stderr!!!',
                                    },
                                    {
                                        id: 3,
                                        work: {
                                            id: 3,
                                            user: { name: 'Student 2', id: 3 },
                                        },
                                        points_achieved: '0 / 13',
                                        state: 'failed',
                                        setup_stdout: 'stdout!!!',
                                        setup_stderr: 'stderr!!!',
                                    },
                                    {
                                        id: 4,
                                        work: {
                                            id: 4,
                                            user: { name: 'Olmo Kramer', id: 4 },
                                        },
                                        points_achieved: '-',
                                        state: 'running',
                                        setup_stdout: 'stdout!!!',
                                        setup_stderr: 'stderr!!!',
                                    },
                                ],
                            },
                        ];

                        this.setTest(test);
                    },
                    err => {
                        if (this.is404(err)) {
                            this.test = null;
                        }
                    },
                );
        },

        loadSingleResult() {
            if (this.test == null) {
                this.setTest(this.testConfig);
            }

            const testId = this.test.id;
            const runId = this.test.runs[0].id;
            const resultId = this.result.id;

            return this.$http
                .get(`/api/v1/auto_tests/${testId}/runs/${runId}/results/${resultId}`)
                .then(
                    ({ data: result }) => {
                        this.result.stepResults = result.step_results;
                    },
                    err => {
                        this.error = err.response.data.message;

                        function randomChoice(choices) {
                            return choices[Math.floor(Math.random() * choices.length)];
                        }

                        const stepResults = {};
                        this.test.sets.forEach(set => {
                            set.suites.forEach(suite => {
                                suite.steps.forEach(step => {
                                    stepResults[step.id] = {
                                        state: randomChoice(['not_started', 'running', 'passed', 'failed']),
                                        log: '{}',
                                    };
                                });
                            });
                        });

                        this.result.stepResults = stepResults;
                    },
                );
        },

        loadPermissions() {
            const names = [
                'can_view_hidden_fixtures',
            ];

            return this.$hasPermission(names, this.assignment.course.id).then(
                perms => {
                    perms.forEach((value, i) => {
                        this.permissions[names[i]] = value;
                    });
                },
            );
        },

        toggleHidden(fixtureIndex) {
            let fun;
            const fixture = this.test.fixtures[fixtureIndex];
            if (fixture.hidden) {
                fun = this.$http.delete;
            } else {
                fun = this.$http.post;
            }
            return fun(`${this.autoTestUrl}/fixtures/${fixture.id}/hide`).then(() => {
                this.$set(this.test.fixtures[fixtureIndex], 'hidden', !fixture.hidden);
            });
        },

        submitContinuePoints(set) {
            return this.$http.patch(`${this.autoTestUrl}/sets/${set.id}`, {
                stop_points: Number(set.stop_points),
            }).then(() => {
                this.$set(set, 'stop_points', Number(set.stop_points));
            });
        },

        setTest(test) {
            this.test = test;
            this.test.sets = test.sets.map(set => ({
                ...set,
                suites: set.suites.map(
                    suite =>
                        new AutoTestSuiteData(
                            this.$http,
                            test.id,
                            set.id,
                            suite,
                        ),
                ),
            }));
        },

        deleteSet(index) {
            return this.$http
                .delete(`${this.autoTestUrl}/sets/${this.test.sets[index].id}`)
                .then(() => index);
        },

        async afterDeleteSet(index) {
            await this.$nextTick();
            this.$set(this.test.sets[index], 'deleted', true);
        },

        openFile(_, event) {
            event.preventDefault();
        },

        selectSetup(selectedName) {
            this.selectedEnvironmentOption = selectedName;
        },

        addSuite(index) {
            this.test.sets[index].suites.push(
                new AutoTestSuiteData(this.$http, this.test.id, this.test.sets[index].id),
            );
            this.$set(this.test.sets, index, this.test.sets[index]);
        },

        addSet() {
            return this.$http.post(`${this.autoTestUrl}/sets/`);
        },

        afterAddSet({ data }) {
            this.test.sets.push(data);
            this.$set(this.test, 'sets', this.test.sets);
        },

        removeFixture(index) {
            return this.$http.patch(this.autoTestUrl, {
                fixtures: this.test.fixtures.filter((_, i) => i !== index),
            });
        },

        async removeFixtureSuccess({ data }) {
            await this.$nextTick();
            this.test.fixtures = data.fixtures;
        },

        submitBaseSystems() {
            return this.$http.patch(this.autoTestUrl, {
                base_systems: this.test.base_systems,
            });
        },

        submitSetupScript() {
            return this.$http.patch(this.autoTestUrl, {
                setup_script: this.test.setup_script,
            });
        },

        submitFinalizeScript() {
            return this.$http.patch(this.autoTestUrl, {
                finalize_script: this.test.finalize_script,
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

            return this.$http.patch(this.autoTestUrl, data);
        },

        afterAddFixtures(response) {
            this.newFixtures = [];
            this.test.fixtures = response.data.fixtures;
        },

        createAutoTest() {
            this.disabledAnimations = true;
            return this.$http.post('/api/v1/auto_tests/', {
                assignment_id: this.assignmentId,
            });
        },

        async afterCreateAutoTest({ data }) {
            this.updateAssignment({
                assignmentId: this.assignmentId,
                assignmentProps: {
                    auto_test_id: data.id,
                },
            });
            this.setTest(data);
            await this.$nextTick();
            this.disabledAnimations = false;
        },

        deleteAutoTest() {
            this.disabledAnimations = true;
            return this.$http.delete(this.autoTestUrl);
        },

        async afterDeleteAutoTest() {
            this.test = null;
            this.updateAssignment({
                assignmentId: this.assignmentId,
                assignmentProps: {
                    auto_test_id: null,
                },
            });
            await this.$nextTick();
            this.disabledAnimations = false;
        },

        deleteResults(id) {
            if (!this.test || !this.test.runs.length) {
                throw new Error('There is no run to delete.');
            }

            return this.$http.delete(
                `/api/v1/auto_tests/${this.assignment.auto_test_id}/runs/${id}`,
            );
        },

        afterDeleteResults() {
            this.test.runs = [];
        },

        is404(err) {
            return getProps(err, null, 'response', 'status') === 404;
        },

        openResult(result) {
            if (result.state !== 'not_started' && result.state !== 'running') {
                this.currentResult = result;
                this.$root.$emit('bv::show::modal', this.resultsModalId);
            }
        },

        canViewFixture(fixture) {
            return !fixture.hidden || this.permissions.can_view_hidden_fixtures;
        },
    },

    computed: {
        autoTestUrl() {
            return `/api/v1/auto_tests/${this.test.id}`;
        },

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
            this.test.base_systems.forEach(t => {
                langSet.add(t.group);
                selectedSet.add(t.id);
            });

            return AutoTestBaseSystems.reduce((res, cur) => {
                if (langSet.has(cur.group) && !selectedSet.has(cur.id)) {
                    res.push(
                        Object.assign(
                            {},
                            {
                                ...cur,
                                $isDisabled: true,
                            },
                        ),
                    );
                } else {
                    res.push(cur);
                }
                return res;
            }, []);
        },

        hasResults() {
            const runs = this.test && this.test.runs;
            return !!(runs && runs.length);
        },

        configEditable() {
            return this.editable && !this.hasResults;
        },

        singleResult() {
            return this.result != null;
        },
    },

    components: {
        Icon,
        Multiselect,
        AutoTestSuite,
        SubmitButton,
        MultipleFilesUploader,
        Loader,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.auto-test.no-border > .card {
    border: 0;
}

.auto-test-suite:not(.empty-auto-test-suite) {
    margin-bottom: 1rem;
}

.auto-test:not(.config-editable) .auto-test-suite:last-child,
.auto-test:not(.config-editable) .auto-test-suite:nth-last-child(2) {
    margin-bottom: 0;
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

    .score,
    .state {
        width: 1px;
        white-space: nowrap;
    }

    .score {
        text-align: right;

        .fa-icon {
            transform: translateY(2px);
            margin-right: .25rem;
        }
    }
}

.setup-output {
    margin-bottom: 0;
    border: 1px solid @color-border-gray-lighter;
    border-top-width: 0;
    border-bottom-left-radius: 0.25rem;
    border-bottom-right-radius: 0.25rem;
    padding: 1rem;
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
</style>
