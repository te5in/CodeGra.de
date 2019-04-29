<template>
<div class="auto-test">
    <b-card no-body>
        <b-card-header class="auto-test-header">
            AutoTest
            <div class="btn-wrapper">
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
                    confirm="Are you sure you want to delete this AutoTest config?"
                    label="Delete"/>
            </div>
        </b-card-header>
        <b-card-body v-if="loading" key="loading">
            <loader/>
        </b-card-body>
        <b-card-body v-else-if="test == null" key="empty">
            <div class="text-muted">You have no AutoTest yet for this assignment</div>
        </b-card-body>
        <b-card-body v-else key="full">
            <div class="setup-env-wrapper">
                <h5>Environment setup</h5>
                <b-form-fieldset>
                    <label :for="baseSystemId">Base system</label>

                    <b-input-group>
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
                                        <div class="fixture-name">
                                            <a href="#" @click="openFile(fixture, $event)">
                                                {{ fixture.name }}
                                            </a>
                                        </div>

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
                                    </li>
                                </transition-group>
                            </ul>
                        </b-form-fieldset>
                    </div>
                </transition>

                <b-form-fieldset class="fixture-upload-wrapper">
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

                <b-form-fieldset>
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
                    <b-card class="test-group auto-test-suite"
                            no-body>
                        <b-card-header class="test-set-header">
                            Test set
                            <div class="btn-wrapper">
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
                                                 :editing="suite.steps.length === 0"
                                                 :key="suite.id"
                                                 :assignment="assignment"
                                                 :other-suites="allNonDeletedSuites"
                                                 @delete="$set(suite, 'deleted', true)"
                                                 v-model="set.suites[j]"/>
                            </masonry>
                            <div class="btn-wrapper"
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
            <div class="add-btn-wrapper transition">
                <submit-button :submit="addSet"
                               @success="afterAddSet"
                               label="Add set"
                               class="transition"/>
        </div>

        <hr/>

        <div class="finalizing-script-wrapper">
            <h5>Finalizing script</h5>
            <b-input-group>
                <input class="form-control"
                       @keydown.ctrl.enter="$refs.finalizeScriptBtn.onClick"
                    v-model="test.finalize_script"/>
                <b-input-group-append>
                    <submit-button :submit="submitFinalizeScript" ref="finalizeScriptBtn"/>
                </b-input-group-append>
            </b-input-group>
        </div>

        <div slot="footer">
            <b-button-toolbar justify>
            </b-button-toolbar>
        </div>
        </b-card-body>
    </b-card>
</div>
</template>

<script>
import Multiselect from 'vue-multiselect';

import { mapActions } from 'vuex';

import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/times';
import 'vue-awesome/icons/eye';
import 'vue-awesome/icons/eye-slash';

import { getUniqueId, getProps, deepCopy, withOrdinalSuffix } from '@/utils';

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
    },

    data() {
        return {
            test: null,
            disabledAnimations: true,
            newFixtures: [],
            loading: true,

            baseSystemId: `auto-test-base-system-${getUniqueId()}`,
            fixtureUploadId: `auto-test-base-upload-${getUniqueId()}`,
            uploadedFixturesId: `auto-test-base-fixtures-${getUniqueId()}`,
            preStartScriptId: `auto-test-base-pre-start-script-${getUniqueId()}`,
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
                this.$http
                    .get(`/api/v1/auto_tests/${this.assignment.auto_test_id}`)
                    .then(
                        ({ data: test }) => this.setTest(test),
                        err => {
                            if (getProps(err, null, 'response', 'status') === 404) {
                                this.test = null;
                            }
                        },
                    )
                    .then(() => {
                        this.loading = false;
                    });
            },
            immediate: true,
        },
    },

    methods: {
        ...mapActions('courses', ['updateAssignment']),

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
                            this.test.id,
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

.auto-test-suite:not(.empty-auto-test-suite) {
    margin-bottom: 1rem;
}

.transition {
    transition: all 0.3s linear;
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
    padding: 5px 1.25rem;
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
    display: flex;
    align-items: center;
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
        &:not(:last-child) {
            border-bottom: 1px solid @color-border-gray-lighter;
        }
        padding: 0.75rem;
        display: flex;
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
</style>
