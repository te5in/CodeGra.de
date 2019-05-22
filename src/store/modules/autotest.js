/* SPDX-License-Identifier: AGPL-3.0-only */
import Vue from 'vue';
import axios from 'axios';

import { deepCopy, getUniqueId, withOrdinalSuffix } from '@/utils';
import * as types from '../mutation-types';

class AutoTestSuiteData {
    constructor(autoTestId, autoTestSetId, serverData = {}, trackingId = getUniqueId()) {
        this.trackingId = trackingId;
        this.autoTestSetId = autoTestSetId;
        this.autoTestId = autoTestId;

        this.id = null;
        this.steps = [];
        this.rubricRow = {};

        this.setFromServerData(serverData);
    }

    setFromServerData(d) {
        Vue.set(this, 'id', d.id);
        Vue.set(this, 'steps', d.steps || []);
        Vue.set(this, 'rubricRow', d.rubric_row || {});
    }

    copy() {
        return new AutoTestSuiteData(
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
        const errors = this.getErrors();

        if (errors != null) {
            const err = new Error('The suite is not valid');
            err.messages = errors;
            return Promise.reject(err);
        }

        return axios
            .patch(this.url, {
                id: this.id == null ? undefined : this.id,
                steps: this.steps.map(step => ({
                    ...step,
                    weight: Number(step.weight),
                })),
                rubric_row_id: this.rubricRow.id,
            })
            .then(
                ({ data }) => {
                    this.setFromServerData(data);
                },
                err => {
                    const newErr = new Error('The suite is not valid');
                    newErr.messages = {
                        general: [err.response.data.message],
                        steps: [],
                    };
                    throw newErr;
                },
            );
    }

    delete() {
        if (this.id != null) {
            return axios.delete(`${this.url}/${this.id}`);
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

class AutoTestResult {
    constructor(result, autoTest) {
        this.id = result.id;
        this.submission = result.work;
        this.update(result, autoTest);
    }

    update(result, autoTest) {
        this.state = result.state;
        this.finished = ['passed', 'failed', 'timed_out'].indexOf(result.state) !== -1;
        this.setupStdout = result.setup_stdout;
        this.setupStderr = result.setup_stderr;
        this.pointsAchieved = result.points_achieved;

        this.updateStepResults(result.step_results, autoTest);
    }

    // eslint-disable-next-line
    updateStepResults(steps, autoTest) {
        if (steps == null) {
            return;
        }

        this.setResults = {};
        this.suiteResults = {};
        this.stepResults = steps.reduce((acc, step) => {
            acc[step.auto_test_step.id] = step;
            return acc;
        }, {});

        let setCheckpointFailed = false;
        autoTest.sets.forEach(set => {
            this.setResults[set.id] = {
                achieved: 0,
                possible: 0,
            };

            set.suites.forEach(suite => {
                let suiteCheckpointFailed = false;
                this.suiteResults[suite.id] = {
                    achieved: 0,
                    possible: 0,
                };

                suite.steps.forEach(step => {
                    this.suiteResults[suite.id].possible += step.weight;

                    if (setCheckpointFailed || suiteCheckpointFailed) {
                        this.stepResults[step.id] = {
                            state: 'skipped',
                            log: null,
                        };
                    } else if (this.stepResults[step.id] == null) {
                        this.stepResults[step.id] = {
                            state: 'not_started',
                            log: null,
                        };
                    } else if (
                        step.type === 'check_points' &&
                        this.stepResults[step.id].state === 'failed'
                    ) {
                        suiteCheckpointFailed = true;
                    } else if (this.stepResults[step.id].state === 'passed') {
                        switch (step.type) {
                            case 'io_test':
                                this.suiteResults[suite.id].achieved += step.data.inputs.reduce(
                                    (acc, input, i) => {
                                        if (
                                            this.stepResults[step.id].log.steps[i].state ===
                                            'passed'
                                        ) {
                                            return acc + input.weight;
                                        } else {
                                            return acc;
                                        }
                                    },
                                    0,
                                );
                                break;
                            default:
                                this.suiteResults[suite.id].achieved += step.weight;
                        }
                    }
                });

                this.setResults[set.id].achieved += this.suiteResults[suite.id].achieved;
                this.setResults[set.id].possible += this.suiteResults[suite.id].possible;

                suite.passed = suiteCheckpointFailed;
            });

            if (this.setResults[set.id] < set.stop_points) {
                setCheckpointFailed = true;
            }

            set.passed = setCheckpointFailed;
        });
    }
}

class AutoTestRun {
    constructor(run, autoTest) {
        this.id = run.id;
        this.results = run.results.map(result => new AutoTestResult(result, autoTest));
        this.update(run, autoTest);
    }

    update(run, autoTest) {
        this.state = run.state;
        this.finished = ['done', 'crashed', 'timed_out'].indexOf(this.state) !== -1;

        this.updateResults(run.results, autoTest);
    }

    updateResults(results, autoTest) {
        results.forEach(r1 => {
            const storeResult = this.results.find(r2 => r2.id === r1.id);
            if (!storeResult.finished) {
                storeResult.update(r1, autoTest);
            }
        });
    }
}

const getters = {
    tests: state => state.tests,
    results: state => state.results,
};

const loaders = {
    tests: {},
    results: {},
    runs: {},
};

const actions = {
    createAutoTest({ commit, dispatch }, assignmentId) {
        return axios
            .post('/api/v1/auto_tests/', {
                assignment_id: assignmentId,
            })
            .then(({ data }) =>
                Promise.all([
                    dispatch(
                        'courses/updateAssignment',
                        {
                            assignmentId,
                            assignmentProps: { auto_test_id: data.id },
                        },
                        { root: true },
                    ),
                    commit(types.SET_AUTO_TEST, data),
                ]),
            );
    },

    deleteAutoTest({ commit, dispatch, state }, autoTestId) {
        if (state.tests[autoTestId] == null) {
            return Promise.resolve();
        }

        const assignmentId = state.tests[autoTestId].assignment_id;

        return axios.delete(`/api/v1/auto_tests/${autoTestId}`).then(() =>
            Promise.all([
                dispatch(
                    'courses/updateAssignment',
                    {
                        assignmentId,
                        assignmentProps: { auto_test_id: null },
                    },
                    { root: true },
                ),
                commit(types.DELETE_AUTO_TEST, autoTestId),
            ]),
        );
    },

    updateAutoTest({ commit }, { autoTestId, autoTestProps }) {
        return axios.patch(`/api/v1/auto_tests/${autoTestId}`, autoTestProps).then(() => {
            commit(types.UPDATE_AUTO_TEST, {
                autoTestId,
                autoTestProps,
            });
        });
    },

    loadAutoTest({ commit, state }, { autoTestId }) {
        if (state.tests[autoTestId] != null) {
            return Promise.resolve();
        }

        if (loaders.tests[autoTestId] == null) {
            loaders.tests[autoTestId] = axios.get(`/api/v1/auto_tests/${autoTestId}`).then(
                ({ data }) => {
                    delete loaders.tests[autoTestId];
                    commit(types.SET_AUTO_TEST, data);
                },
                err => {
                    delete loaders.tests[autoTestId];
                    throw new Error(err.response.data.message);
                },
            );
        }

        return loaders.tests[autoTestId];
    },

    async createAutoTestRun({ commit, dispatch, state }, { autoTestId }) {
        await dispatch('loadAutoTest', { autoTestId });
        const autoTest = state.tests[autoTestId];

        if (autoTest.runs.length > 0) {
            throw new Error('AutoTest has already been run.');
        }

        return axios
            .post(`/api/v1/auto_tests/${autoTestId}/runs/`)
            .then(
                ({ data }) =>
                    commit(types.UPDATE_AUTO_TEST_RUNS, { autoTest, run: data }),
                err => {
                    throw new Error(err.response.data.message);
                },
            );
    },

    async loadAutoTestRun({ commit, dispatch, state }, { autoTestId }) {
        await dispatch('loadAutoTest', { autoTestId });
        const autoTest = state.tests[autoTestId];

        const oldRun = autoTest.runs[0];
        if (!oldRun) {
            throw new Error('AutoTest has not been run yet.');
        } else if (oldRun.done) {
            return null;
        }

        const runId = oldRun.id;
        if (loaders.runs[runId] == null) {
            loaders.runs[runId] = axios.get(`/api/v1/auto_tests/${autoTestId}/runs/${runId}`).then(
                ({ data }) => {
                    delete loaders.runs[runId];
                    commit(types.UPDATE_AUTO_TEST_RUNS, { autoTest, run: data });
                },
                err => {
                    delete loaders.runs[runId];
                    throw new Error(err.response.data.message);
                },
            );
        }

        return loaders.runs[runId];
    },

    async createAutoTestSet({ commit, dispatch, state }, { autoTestId }) {
        await dispatch('loadAutoTest', { autoTestId });
        const autoTest = state.tests[autoTestId];

        return axios.post(`/api/v1/auto_tests/${autoTestId}/sets/`).then(({ data }) =>
            commit(types.UPDATE_AUTO_TEST, {
                autoTestId,
                autoTestProps: {
                    sets: [...autoTest.sets, data],
                },
            }),
        );
    },

    async deleteAutoTestSet({ commit, dispatch, state }, { autoTestId, setId }) {
        await dispatch('loadAutoTest', { autoTestId });
        const autoTest = state.tests[autoTestId];

        return axios.delete(`/api/v1/auto_tests/${autoTestId}/sets/${setId}`).then(() =>
            commit(types.UPDATE_AUTO_TEST, {
                autoTestId,
                autoTestProps: {
                    sets: autoTest.sets.filter(set => set.id !== setId),
                },
            }),
        );
    },

    updateAutoTestSet({ commit }, { autoTestId, autoTestSet, setProps }) {
        return axios
            .patch(`/api/v1/auto_tests/${autoTestId}/sets/${autoTestSet.id}`, setProps)
            .then(() =>
                commit(types.UPDATE_AUTO_TEST_SET, {
                    autoTestSet,
                    setProps,
                }),
            );
    },

    createAutoTestSuite({ commit }, { autoTestId, autoTestSet }) {
        const suites = autoTestSet.suites.concat(new AutoTestSuiteData(autoTestId, autoTestSet.id));

        return commit(types.UPDATE_AUTO_TEST_SET, {
            autoTestSet,
            setProps: { suites },
        });
    },

    deleteAutoTestSuite({ commit }, { autoTestSuite }) {
        return commit(types.DELETE_AUTO_TEST_SUITE, {
            autoTestSuite,
        });
    },

    updateAutoTestSuite({ commit }, { autoTestSet, index, suite }) {
        const suites = [...autoTestSet.suites];
        suites[index] = suite;

        return commit(types.UPDATE_AUTO_TEST_SET, {
            autoTestSet,
            setProps: { suites },
        });
    },

    async loadAutoTestResult({ commit, dispatch, state }, { autoTestId, submissionId }) {
        await dispatch('loadAutoTest', { autoTestId });
        const autoTest = state.tests[autoTestId];

        if (autoTest.runs.length === 0) {
            throw new Error('AutoTest has not been run yet.');
        }

        let result = autoTest.runs[0].results.find(r => r.submission.id === submissionId);
        const resultId = result && result.id;

        if (resultId == null) {
            throw new Error('AutoTest result not found!');
        }

        result = state.results[resultId];
        if (result && result.done) {
            return null;
        }

        if (loaders.results[resultId] == null) {
            loaders.results[resultId] = axios
                .get(
                    `/api/v1/auto_tests/${autoTestId}/runs/${
                        autoTest.runs[0].id
                    }/results/${resultId}`,
                )
                .then(
                    ({ data }) => {
                        delete loaders.results[resultId];
                        commit(types.UPDATE_AUTO_TEST_RESULT, { autoTest, result: data });
                    },
                    err => {
                        delete loaders.results[resultId];
                        throw new Error(err.response.data.message);
                    },
                );
        }

        return loaders.results[resultId];
    },

    async deleteAutoTestResults({ commit, dispatch, state }, { autoTestId, runId }) {
        await dispatch('loadAutoTest', { autoTestId });
        const autoTest = state.tests[autoTestId];

        if (autoTest.runs.length === 0) {
            return null;
        }

        return axios.delete(`/api/v1/auto_tests/${autoTestId}/runs/${runId}`).then(() =>
            commit(types.UPDATE_AUTO_TEST, {
                autoTestId,
                autoTestProps: {
                    runs: autoTest.runs.filter(run => run.id !== runId),
                },
            }),
        );
    },

    createFixtures({ commit }, { autoTestId, fixtures }) {
        return axios.patch(`/api/v1/auto_tests/${autoTestId}`, fixtures).then(({ data }) =>
            commit(types.UPDATE_AUTO_TEST, {
                autoTestId,
                autoTestProps: { fixtures: data.fixtures },
            }),
        );
    },

    async toggleFixture({ commit, dispatch, state }, { autoTestId, fixture }) {
        await dispatch('loadAutoTest', { autoTestId });
        const autoTest = state.tests[autoTestId];

        const hidden = !fixture.hidden;
        const method = fixture.hidden ? 'delete' : 'post';

        return axios[method](`/api/v1/auto_tests/${autoTestId}/fixtures/${fixture.id}/hide`).then(
            () => {
                const fixtures = deepCopy(autoTest.fixtures);
                fixtures.find(f => f.id === fixture.id).hidden = hidden;

                commit(types.UPDATE_AUTO_TEST, {
                    autoTestId,
                    autoTestProps: { fixtures },
                });
            },
        );
    },
};

const mutations = {
    [types.SET_AUTO_TEST](state, autoTest) {
        autoTest.sets.forEach(set => {
            set.suites = set.suites.map(suite => new AutoTestSuiteData(autoTest.id, set.id, suite));
        });

        autoTest.pointsPossible = autoTest.sets.reduce(
            (acc1, set) =>
                acc1 +
                set.suites.reduce(
                    (acc2, suite) =>
                        acc2 + suite.steps.reduce((acc3, step) => acc3 + step.weight, 0),
                    0,
                ),
            0,
        );

        autoTest.runs = autoTest.runs.map(run => new AutoTestRun(run, autoTest));

        Vue.set(state.tests, autoTest.id, autoTest);
    },

    [types.DELETE_AUTO_TEST](state, autoTestId) {
        state.tests[autoTestId].runs.forEach(run =>
            run.results.forEach(result =>
                Vue.delete(state.results, result.id),
            ),
        );

        Vue.delete(state.tests, autoTestId);
    },

    [types.UPDATE_AUTO_TEST](state, { autoTestId, autoTestProps }) {
        const autoTest = state.tests[autoTestId];

        Object.entries(autoTestProps).forEach(([k, v]) => Vue.set(autoTest, k, v));
    },

    [types.UPDATE_AUTO_TEST_RUNS](state, { autoTest, run }) {
        console.log('updating runs!');

        let runIndex = autoTest.runs.findIndex(r => r.id === run.id);
        let storeRun;

        if (runIndex === -1) {
            storeRun = new AutoTestRun(run, autoTest);
            runIndex = 0;
        } else {
            storeRun = autoTest.runs[runIndex];
            storeRun.update(run, autoTest);
        }

        Vue.set(autoTest.runs, runIndex, storeRun);
    },

    [types.UPDATE_AUTO_TEST_SET](state, { autoTestSet, setProps }) {
        Object.entries(setProps).forEach(([k, v]) => Vue.set(autoTestSet, k, v));
    },

    [types.DELETE_AUTO_TEST_SUITE](state, { autoTestSuite }) {
        Vue.set(autoTestSuite, 'deleted', true);
    },

    [types.UPDATE_AUTO_TEST_RESULT](state, { result, autoTest }) {
        const run = autoTest.runs[0];
        const resultIndex = run.results.findIndex(r => r.id === result.id);
        const storeResult = run.results[resultIndex];
        storeResult.update(result, autoTest);

        Vue.set(run.results, resultIndex, storeResult);
        Vue.set(state.results, result.id, storeResult);
    },
};

export default {
    namespaced: true,
    state: {
        tests: {},
        results: {},
    },
    getters,
    actions,
    mutations,
};
