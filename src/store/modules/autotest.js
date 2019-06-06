/* SPDX-License-Identifier: AGPL-3.0-only */
import Vue from 'vue';
import axios from 'axios';

import { deepCopy, withOrdinalSuffix, getProps } from '@/utils';
import * as types from '../mutation-types';

class AutoTestSuiteData {
    constructor(autoTestId, autoTestSetId, serverData = {}) {
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
        Vue.set(
            this,
            'commandTimeLimit',
            getProps(
                d,
                UserConfig.features.autoTest.auto_test_max_command_time,
                'command_time_limit',
            ),
        );
        Vue.set(this, 'networkDisabled', getProps(d, true, 'network_disabled'));
    }

    copy() {
        return new AutoTestSuiteData(this.autoTestId, this.autoTestSetId, {
            id: this.id,
            steps: deepCopy(this.steps),
            rubric_row: this.rubricRow,
            network_disabled: this.networkDisabled,
            command_time_limit: this.commandTimeLimit,
        });
    }

    isEmpty() {
        return this.steps.length === 0;
    }

    isValid() {
        return !this.isEmpty() && !this.deleted;
    }

    get url() {
        return `/api/v1/auto_tests/${this.autoTestId}/sets/${this.autoTestSetId}/suites/`;
    }

    save() {
        const errors = this.getErrors();

        if (errors != null) {
            const err = new Error('The category is not valid');
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
                command_time_limit: Number(this.commandTimeLimit),
                network_disabled: getProps(this, true, 'networkDisabled'),
            })
            .then(
                res => {
                    this.setFromServerData(res.data);
                    return res;
                },
                err => {
                    const newErr = new Error('The category is not valid');
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

        if (isEmpty(step.name)) {
            errs.push('The name may not be empty.');
        }

        const program = getProps(step, null, 'data', 'program');
        if (program != null && isEmpty(program)) {
            errs.push('The program may not be empty.');
        }

        if (step.type !== 'check_points' && Number(step.weight) <= 0) {
            errs.push('The weight should be a number greater than 0.');
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
                        errs.push(`The weight of the ${name} should be a number greater than 0.`);
                    }
                });
            }
        } else if (step.type === 'check_points') {
            let weightBefore = 0;
            for (let i = 0; i < this.steps.length > 0; ++i) {
                if (this.steps[i] === step) {
                    break;
                }
                weightBefore += Number(this.steps[i].weight);
            }
            if (step.data.min_points <= 0 || step.data.min_points > weightBefore) {
                errs.push(
                    `The minimal amount of points should be achievable (at most
                    ${weightBefore}) and greater than 0.`,
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
            caseErrors.general.push('You should select a rubric category for this test category.');
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
        this.finished = this.isFinishedState(result.state);
        this.startedAt = result.started_at;
        this.pointsAchieved = result.points_achieved;

        this.updateStepResults(result.step_results, autoTest);
    }

    updateExtended(result, autoTest) {
        this.update(result, autoTest);
        this.setupStdout = result.setup_stdout;
        this.setupStderr = result.setup_stderr;
    }

    updateStepResults(steps, autoTest) {
        if (steps == null) {
            return;
        }

        const stepResults = steps.reduce((acc, step) => {
            acc[step.auto_test_step.id] = step;
            return acc;
        }, {});

        const setResults = {};
        const suiteResults = {};

        let setFailed = false;
        let totalAchieved = 0;

        autoTest.sets.forEach(set => {
            if (set.deleted) return;

            const setResult = {
                achieved: totalAchieved,
                possible: 0,
                finished: false,
            };

            setResult.suiteResults = set.suites.map(suite => {
                if (suite.deleted) {
                    return null;
                }

                let suiteFailed = false;

                const suiteResult = {
                    achieved: 0,
                    possible: 0,
                    finished: true,
                };

                suiteResult.stepResults = suite.steps.map(step => {
                    suiteResult.possible += step.weight;

                    let stepResult = stepResults[step.id];

                    if (stepResult == null) {
                        stepResult = {
                            state: setFailed || suiteFailed ? 'skipped' : 'not_started',
                            log: null,
                        };
                    }

                    stepResult.finished = this.isFinishedState(stepResult.state);

                    if (step.type === 'check_points' && stepResult.state !== 'passed') {
                        suiteFailed = true;
                    } else {
                        suiteResult.achieved += getProps(stepResult, 0, 'achieved_points');
                    }

                    stepResults[step.id] = stepResult;
                    return stepResult;
                });

                suiteResult.finished = suiteResult.stepResults.every(s => s.finished);
                suiteResults[suite.id] = suiteResult;

                setResult.achieved += suiteResult.achieved;
                setResult.possible += suiteResult.possible;

                suiteResults[suite.id] = suiteResult;
                return suiteResult;
            });

            totalAchieved = setResult.achieved;
            setResult.finished = setResult.suiteResults.every(s => s && s.finished);

            if (setResult.finished && totalAchieved <= set.stop_points) {
                setFailed = true;
            }

            setResults[set.id] = setResult;
        });

        Vue.set(this, 'stepResults', stepResults);
        Vue.set(this, 'suiteResults', suiteResults);
        Vue.set(this, 'setResults', setResults);
    }

    // eslint-disable-next-line
    isFinishedState(state) {
        return ['passed', 'failed', 'timed_out'].indexOf(state) !== -1;
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
        this.setupStdout = run.setup_stdout;
        this.setupStderr = run.setup_stderr;

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
                    throw err;
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
            .then(({ data }) => commit(types.UPDATE_AUTO_TEST_RUNS, { autoTest, run: data }));
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
                    throw err;
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
        const suites = [...autoTestSet.suites, new AutoTestSuiteData(autoTestId, autoTestSet.id)];

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
                        throw err;
                    },
                );
        }

        return loaders.results[resultId];
    },

    async deleteAutoTestResults({ commit, dispatch, state }, { autoTestId, runId, force }) {
        await dispatch('loadAutoTest', { autoTestId });
        const autoTest = state.tests[autoTestId];

        if (autoTest.runs.length === 0) {
            return null;
        }

        const c = () =>
            commit(types.UPDATE_AUTO_TEST, {
                autoTestId,
                autoTestProps: {
                    runs: autoTest.runs.filter(run => run.id !== runId),
                },
            });

        return axios
            .delete(`/api/v1/auto_tests/${autoTestId}/runs/${runId}`)
            .then(c, () => force && c());
    },

    createFixtures({ commit }, { autoTestId, fixtures, delay }) {
        return axios.patch(`/api/v1/auto_tests/${autoTestId}`, fixtures).then(async res => {
            await Promise.resolve([
                commit(types.UPDATE_AUTO_TEST, {
                    autoTestId,
                    autoTestProps: { fixtures: res.data.fixtures },
                }),
                new Promise(resolve => {
                    setTimeout(resolve, delay == null ? 500 : delay);
                }),
            ]);
            return res;
        });
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

        Object.defineProperty(autoTest, 'pointsPossible', {
            get() {
                return autoTest.sets.reduce((acc1, set) => {
                    if (set.deleted) {
                        return acc1;
                    }

                    return (
                        acc1 +
                        set.suites.reduce((acc2, suite) => {
                            if (suite.deleted) {
                                return acc2;
                            }

                            return acc2 + suite.steps.reduce((acc3, step) => acc3 + step.weight, 0);
                        }, 0)
                    );
                }, 0);
            },
        });

        autoTest.runs = autoTest.runs.map(run => new AutoTestRun(run, autoTest));

        Vue.set(state.tests, autoTest.id, autoTest);
    },

    [types.DELETE_AUTO_TEST](state, autoTestId) {
        state.tests[autoTestId].runs.forEach(run =>
            run.results.forEach(result => Vue.delete(state.results, result.id)),
        );

        Vue.delete(state.tests, autoTestId);
    },

    [types.UPDATE_AUTO_TEST](state, { autoTestId, autoTestProps }) {
        const autoTest = state.tests[autoTestId];

        Object.entries(autoTestProps).forEach(([k, v]) => Vue.set(autoTest, k, v));
    },

    [types.UPDATE_AUTO_TEST_RUNS](state, { autoTest, run }) {
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

        storeResult.updateExtended(result, autoTest);

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
