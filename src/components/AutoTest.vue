<template>
<b-alert v-if="message && message.isError"
         show
         variant="danger"
         class="error-message mb-3">
    {{ message.text }}
</b-alert>

<div v-else-if="message" class="text-muted font-italic p-3">
    {{ message.text }}
</div>

<loader v-else-if="loading" />

<div v-else class="auto-test" :class="{ editable }">
    <template v-if="autoTestRun && !singleResult">
        <auto-test-run
            v-for="run in test.runs"
            :key="`auto-test-run-${run.id}`"
            class="mb-3"
            :assignment="assignment"
            :auto-test="test"
            :run="run"
            :editable="editable"
            @open-result="openResult"
            @results-deleted="afterDeleteResults" />
    </template>

    <b-card no-body>
        <collapse v-model="configCollapsed">
            <b-card-header v-if="editable"
                           slot="handle"
                           class="py-1 d-flex justify-content-between align-items-center">
                <span class="toggle">
                    <icon name="chevron-down" :scale="0.75" />
                    Configuration
                </span>

                <div v-b-popover.hover.top="createAutoTestPopover">
                    <submit-button
                        v-if="!loading && test == null"
                        label="Create AutoTest"
                        key="create-btn"
                        :disabled="this.assignment.rubric == null"
                        :submit="createAutoTest"
                        @success="afterCreateAutoTest"/>

                    <submit-button
                        v-if="!loading && test != null"
                        label="Run"
                        :submit="runAutoTest"
                        :disabled="!configEditable"/>

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

            <b-card-body v-if="test == null"
                         slot="content"
                         key="empty"
                         class="text-muted font-italic">
                You have no AutoTest yet for this assignment
            </b-card-body>
            <b-card-body v-else
                         slot="content"
                         key="full"
                         class="setup-env-wrapper">
                <b-card no-body>
                    <collapse v-model="setupCollapsed" :disabled="!singleResult">
                        <b-card-header slot="handle">
                            <span class="toggle">
                                <icon v-if="singleResult" name="chevron-down" :scale="0.75" />
                                Setup
                            </span>
                        </b-card-header>

                        <b-card-body v-if="!configEditable && !hasEnvironmentSetup"
                                     slot="content"
                                     class="text-muted font-italic">
                            No fixtures or setup scripts were defined.
                        </b-card-body>

                        <b-card-body v-else slot="content">
                            <b-form-fieldset v-if="test.fixtures.length">
                                <label :for="uploadedFixturesId">
                                    Uploaded fixtures
                                </label>

                                <ul class="fixture-list border rounded p-0 mb-0">
                                    <li v-for="fixture, index in test.fixtures"
                                        class="px-3 py-1 d-flex align-items-center justify-content-between border-bottom"
                                        :key="fixture.id">
                                        <a v-if="canViewFixture(fixture)"
                                            class="flex-grow-1"
                                            href="#"
                                            @click.capture.prevent.stop="downloadFixture(fixture)">
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
                                                v-b-popover.top.hover="`This fixture is hidden. ${singleResult && !canViewFixture(fixture) ? 'You' : 'Students'} may not view its contents.`"/>
                                    </li>
                                </ul>
                            </b-form-fieldset>

                            <b-form-fieldset v-if="configEditable">
                                <label :for="fixtureUploadId">
                                    Upload fixtures
                                </label>

                                <multiple-files-uploader
                                    v-model="newFixtures"
                                    :id="fixtureUploadId">
                                    Click here or drop file(s) add fixtures and test files.
                                </multiple-files-uploader>

                                <b-input-group class="justify-content-end border rounded-bottom">
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

                                <div v-else-if="test.run_setup_script">
                                    <code>{{ test.run_setup_script }}</code>

                                    <template v-if="result">
                                        <b-tabs no-fade>
                                            <b-tab title="stdout">
                                                <pre class="border border-top-0 rounded-bottom"
                                                    :class="{ 'text-muted': !autoTestRun.setupStdout }">{{
                                                    autoTestRun.setupStdout || 'No output.'
                                                }}</pre>
                                            </b-tab>

                                            <b-tab title="stderr">
                                                <pre class="border border-top-0 rounded-bottom"
                                                    :class="{ 'text-muted': !autoTestRun.setupStderr }">{{
                                                    autoTestRun.setupStderr || 'No output.'
                                                }}</pre>
                                            </b-tab>
                                        </b-tabs>
                                    </template>
                                </div>
                            </b-form-fieldset>

                            <b-form-fieldset v-if="configEditable || test.setup_script">
                                <label :for="preStartScriptId">
                                    Setup script to run
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

                                <div v-else-if="test.setup_script">
                                    <code>{{ test.setup_script }}</code>

                                    <template v-if="result">
                                        <b-tabs no-fade>
                                            <b-tab title="stdout">
                                                <pre class="border border-top-0 rounded-bottom"
                                                    :class="{ 'text-muted': !result.setupStdout }">{{
                                                    result.setupStdout || 'No output.'
                                                }}</pre>
                                            </b-tab>

                                            <b-tab title="stderr">
                                                <pre class="border border-top-0 rounded-bottom"
                                                    :class="{ 'text-muted': !result.setupStderr }">{{
                                                    result.setupStderr || 'No output.'
                                                }}</pre>
                                            </b-tab>
                                        </b-tabs>
                                    </template>
                                </div>
                            </b-form-fieldset>
                        </b-card-body>
                    </collapse>
                </b-card>

                <p class="text-muted font-italic mt-3"
                   v-if="test.sets.filter(s => !s.deleted).length === 0">
                    You have no levels yet. Click the button below to create one.
                </p>

                <h5 v-if="singleResult" class="mt-3">
                    Categories
                </h5>

                <div v-for="set, i in test.sets"
                    v-if="!set.deleted"
                    :key="set.id"
                    class="mt-3">
                    <auto-test-set :value="set"
                                :assignment="assignment"
                                :editable="configEditable"
                                :result="result"
                                :other-suites="allNonDeletedSuites"
                                :animations="disabledAnimations" />
                </div>

                <b-button-toolbar v-if="configEditable"
                    class="mt-3 justify-content-end">
                    <submit-button :submit="addSet"
                                label="Add level" />
                </b-button-toolbar>
            </b-card-body>
        </collapse>
    </b-card>

    <b-modal
        v-if="currentResult"
        :id="resultsModalId"
        hide-footer
        @hidden="currentResult = null"
        class="result-modal">
        <template slot="modal-title">
            {{ $utils.nameOfUser(currentResult.submission.user) }} -
            {{ currentResult.pointsAchieved }} / {{ test.pointsPossible }} points
        </template>

        <auto-test
            :assignment="assignment"
            :submission-id="currentResult.submission.id" />

        <rubric-viewer
            class="mx-3 mb-3"
            :assignment="assignment"
            :submission="currentResult.submission"
            :rubric="currentResult.rubric" />
    </b-modal>
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

import Collapse from './Collapse';
import AutoTestRun from './AutoTestRun';
import AutoTestSet from './AutoTestSet';
import AutoTestState from './AutoTestState';
import SubmitButton from './SubmitButton';
import MultipleFilesUploader from './MultipleFilesUploader';
import RubricViewer from './RubricViewer';
import Loader from './Loader';

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
    },

    data() {
        const id = this.$utils.getUniqueId();
        const singleResult = this.submissionId != null;

        return {
            disabledAnimations: true,
            newFixtures: [],
            internalTest: {},
            loading: true,
            message: null,
            permissions: {},
            currentResult: null,
            pollingInterval: 3000,
            pollingTimer: null,

            configCollapsed: !singleResult,
            setupCollapsed: singleResult,

            configCollapseId: `auto-test-config-collapse-${id}`,
            fixtureUploadId: `auto-test-base-upload-${id}`,
            uploadedFixturesId: `auto-test-base-fixtures-${id}`,
            preStartScriptId: `auto-test-base-pre-start-script-${id}`,
            globalPreStartScriptId: `auto-test-base-pre-start-script-${id}`,
            autoTestSetupEnvWrapperId: `auto-test-setup-env-${id}`,
            resultsModalId: `auto-test-results-modal-${id}`,
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
                if (this.autoTestId == null) {
                    this.loading = false;
                    return;
                }

                this.loading = true;

                Promise.all([this.loadAutoTest(), this.loadPermissions()]).then(
                    () => {},
                    () => {},
                ).then(() => {
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
            storeLoadAutoTestResult: 'loadAutoTestResult',
            storeCreateAutoTestSet: 'createAutoTestSet',
        }),

        runAutoTest() {
            this.storeCreateAutoTestRun({
                autoTestId: this.autoTestId,
            }).then(() => {
                this.configCollapsed = true;
                return this.loadAutoTestRun();
            });
        },

        loadAutoTest() {
            return this.storeLoadAutoTest({
                autoTestId: this.autoTestId,
            }).then(
                () => {
                    this.configCollapsed = !!this.autoTestRun && !this.singleResult;

                    this.loadAutoTestRun();
                    this.message = null;
                    return this.loadSingleResult();
                },
                err => {
                    this.message = {
                        text: `Could not load AutoTest: ${this.$utils.getErrorMessage(err)}`,
                        isError: true,
                    };
                },
            );
        },

        loadAutoTestRun() {
            if (!this.autoTestRun || this.singleResult || this.test.runs[0].finished) {
                return;
            }

            this.pollingTimer = setTimeout(() => {
                this.storeLoadAutoTestRun({
                    autoTestId: this.autoTestId,
                }).then(
                    () => this.loadAutoTestRun(),
                    err => {
                        switch (this.$utils.getProps(err, 500, 'response', 'status')) {
                            case 404:
                                clearTimeout(this.pollingTimer);
                                if (this.autoTestRun) {
                                    this.storeDeleteAutoTestResults({
                                        autoTestId: this.autoTestId,
                                        runId: this.autoTestRun.id,
                                        force: true,
                                    });
                                }
                                break;
                            case 500:
                                this.loadAutoTestRun();
                                break;
                            default:
                                clearTimeout(this.pollingTimer);
                                break;
                        }
                    },
                );
            }, this.pollingInterval);
        },

        loadSingleResult() {
            if (!this.singleResult) {
                return null;
            }

            return this.storeLoadAutoTestResult({
                autoTestId: this.autoTestId,
                submissionId: this.submissionId,
            }).then(
                () => {
                    if (!this.result.finished) {
                        this.pollingTimer = setTimeout(this.loadSingleResult, this.pollingInterval);
                    }
                    this.message = null;
                },
                err => {
                    this.message = {
                        text: this.$utils.getErrorMessage(err),
                        isError: false,
                    };
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

            this.storeUpdateAutoTest({
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

        downloadFixture(fixture) {
            if (fixture.hidden && !this.permissions.can_view_hidden_fixtures) {
                throw new Error('You do not have permission to view the content of this fixture.');
            }

            this.$http
                .get(`/api/v1/auto_tests/${this.autoTestId}/fixtures/${fixture.id}`)
                .then(({ data }) => {
                    this.$utils.downloadFile(data, fixture.name, 'application/octet-stream');
                });
        },

        createAutoTest() {
            if (this.singleResult) {
                throw new Error('AutoTest cannot be created on a single result page.');
            }

            this.disabledAnimations = true;
            return this.storeCreateAutoTest(this.assignment.id);
        },

        async afterCreateAutoTest() {
            await this.$nextTick();
            this.disabledAnimations = false;
            this.configCollapsed = false;
        },

        deleteAutoTest() {
            if (this.singleResult) {
                throw new Error('AutoTest cannot be deleted on a single result page.');
            }

            this.disabledAnimations = true;
            return this.storeDeleteAutoTest(this.autoTestId);
        },

        async afterDeleteAutoTest() {
            await this.$nextTick();
            this.disabledAnimations = false;
        },

        canViewFixture(fixture) {
            return !fixture.hidden || this.permissions.can_view_hidden_fixtures;
        },

        addSet() {
            return this.storeCreateAutoTestSet({
                autoTestId: this.autoTestId,
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
                    rubrics: this.$utils.deepCopy(this.assignment.rubric),
                }),
            });

            await this.$nextTick();
            this.$root.$emit('bv::show::modal', this.resultsModalId);
        },
    },

    computed: {
        ...mapGetters('autotest', {
            storeTests: 'tests',
            storeResults: 'results',
        }),

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
            return this.editable && !this.autoTestRun;
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
            return this.test.runs[0].results.find(r => r.submission.id === this.submissionId);
        },

        createAutoTestPopover() {
            if (this.assignment.rubric == null) {
                return 'You cannot create an AutoTest for this assignment because it does not have a rubric.';
            } else if (this.editable && !this.configEditable) {
                return 'The AutoTest cannot be run or deleted because there are results associated with it.';
            } else {
                return '';
            }
        },

        hasEnvironmentSetup() {
            return (
                this.test != null &&
                this.test.fixtures.length != null &&
                this.test.setup_script != null &&
                this.test.run_setup_script != null
            );
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
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.auto-test:not(.editable) > .card {
    border: 0;
}

.transition {
    transition: all 0.3s linear;
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
    overflow-y: hidden;
    margin-bottom: 0;
}

.emptytext-enter,
.emptytext-leave-to {
    max-height: 0;
    overflow-y: hidden;
    margin: 0 !important;
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

.fixture-list {
    min-height: 2.5rem;
    max-height: 15rem;
    overflow: auto;
}

.setup-env-wrapper {
    fieldset {
        &:last-child {
            margin-bottom: 0;
        }
    }

    pre {
        margin-bottom: 0;
        border: 1px solid @color-border-gray-lighter;
        border-top-width: 0;
        border-bottom-left-radius: 0.25rem;
        border-bottom-right-radius: 0.25rem;
        padding: 1rem;

        #app.dark & {
            color: @text-color-dark;
            border-color: @color-primary-darker;
        }
    }
}
</style>

<style lang="less">
.auto-test {
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
}

.toggle {
    .auto-test & .fa-icon {
        margin-right: 0.5rem;
        transition: transform 300ms;
    }

    .auto-test .x-collapsing > .handle & .fa-icon,
    .auto-test .x-collapsed > .handle & .fa-icon {
        transform: rotate(-90deg);
    }
}
</style>
