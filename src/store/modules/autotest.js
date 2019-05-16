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
    constructor(result) {
        this.id = result.id;
        this.submission = result.work;
        this.state = result.state;
        this.setupStdout = result.setup_stdout;
        this.setupStderr = result.setup_stderr;

        this.updateStepResults(result);
    }

    // eslint-disable-next-line
    updateStepResults(result) {
        if (result.step_results == null) {
            return;
        }

        const setResults = {};
        const suiteResults = {};
        const stepResults = result.step_results.reduce(
            (acc, step) => {
                acc[step.auto_test_step.id] = step;
                return acc;
            },
            {},
        );

        this.setResults = setResults;
        this.suiteResults = suiteResults;
        this.stepResults = stepResults;

        let setCheckpointFailed = false;
        result.autoTest.sets.forEach(set => {
            setResults[set.id] = {
                achieved: 0,
                possible: 0,
            };

            set.suites.forEach(suite => {
                let suiteCheckpointFailed = false;
                suiteResults[suite.id] = {
                    achieved: 0,
                    possible: 0,
                };

                suite.steps.forEach(step => {
                    suiteResults[suite.id].possible += step.weight;

                    if (setCheckpointFailed || suiteCheckpointFailed) {
                        stepResults[step.id] = {
                            state: 'skipped',
                            log: null,
                        };
                    } else if (stepResults[step.id] == null) {
                        stepResults[step.id] = {
                            state: 'not_started',
                            log: null,
                        };
                    } else if (
                        step.type === 'check_points' &&
                        stepResults[step.id].state === 'failed'
                    ) {
                        suiteCheckpointFailed = true;
                    } else if (stepResults[step.id].state === 'passed') {
                        switch (step.type) {
                            case 'io_test':
                                suiteResults[suite.id].achieved += step.data.inputs.reduce(
                                    (acc, input, i) => {
                                        if (stepResults[step.id].log.steps[i].state === 'passed') {
                                            return acc + input.weight;
                                        } else {
                                            return acc;
                                        }
                                    },
                                    0,
                                );
                                break;
                            default:
                                suiteResults[suite.id].achieved += step.weight;
                        }
                    }
                });

                setResults[set.id].achieved += suiteResults[suite.id].achieved;
                setResults[set.id].possible += suiteResults[suite.id].possible;

                suite.passed = suiteCheckpointFailed;
            });

            if (setResults[set.id] < set.stop_points) {
                setCheckpointFailed = true;
            }

            set.passed = setCheckpointFailed;
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
};

const actions = {
    createAutoTest({ commit, dispatch, state }, assignmentId) {
        return axios.post('/api/v1/auto_tests/', {
            assignment_id: assignmentId,
        }).then(
            ({ data }) => Promise.all([
                dispatch('courses/updateAssignment', {
                    assignmentId,
                    assignmentProps: { auto_test_id: data.id },
                }, { root: true }),
                commit(types.SET_AUTO_TEST, data),
            ]).then(
                // eslint-disable-next-line
                () => state.tests[data.id],
            ),
        );
    },

    deleteAutoTest({ commit, dispatch, state }, autoTestId) {
        if (state.tests[autoTestId] == null) {
            return Promise.resolve();
        }

        const assignmentId = state.tests[autoTestId].assignment_id;

        return axios.delete(`/api/v1/auto_tests/${autoTestId}`).then(
            () => Promise.all([
                dispatch('courses/updateAssignment', {
                    assignmentId,
                    assignmentProps: { auto_test_id: null },
                }, { root: true }),
                commit(types.DELETE_AUTO_TEST, autoTestId),
            ]),
        );
    },

    updateAutoTest({ commit, state }, { autoTestId, autoTestProps }) {
        return axios
            .patch(`/api/v1/auto_tests/${autoTestId}`, autoTestProps)
            .then(() => {
                commit(types.UPDATE_AUTO_TEST, {
                    autoTestId,
                    autoTestProps,
                });
                return state.tests[autoTestId];
            });
    },

    loadAutoTest({ commit, state }, { autoTestId }) {
        if (state.tests[autoTestId] != null) {
            return Promise.resolve(state.tests[autoTestId]);
        }

        if (loaders.tests[autoTestId] == null) {
            loaders.tests[autoTestId] = axios
                .get(`/api/v1/auto_tests/${autoTestId}`)
                .then(
                    // ({ data }) => commit(types.SET_AUTO_TEST, data),
                    // FIXME: remove
                    () => commit(types.SET_AUTO_TEST, {
                        id: autoTestId,
                        assignment_id: 3,
                        base_systems: [
                            {
                                group: 'python',
                                id: 2,
                                name: 'Python 3.6',
                            },
                        ],
                        finalize_script: '',
                        fixtures: [
                            {
                                hidden: true,
                                id: 1,
                                name: 'Programmeertalen-Go (1).csv',
                            },
                            {
                                hidden: false,
                                id: 3,
                                name: 'Programmeertalen-Python (1).csv',
                            },
                            {
                                hidden: true,
                                id: 4,
                                name: 'Programmeertalen-Python (2).csv',
                            },
                            {
                                hidden: false,
                                id: 2,
                                name: 'Programmeertalen-Python.csv',
                            },
                        ],
                        sets: [
                            {
                                id: 1,
                                stop_points: 3,
                                suites: [
                                    {
                                        autoTestSetId: 1,
                                        autoTestId: 1,
                                        id: 1,
                                        steps: [
                                            {
                                                data: {
                                                    inputs: [
                                                        {
                                                            args: 'abc',
                                                            id: 4,
                                                            name: 'Sort 1',
                                                            options: [],
                                                            output: 'cba',
                                                            stdin: 'abc',
                                                            weight: 1,
                                                        },
                                                        {
                                                            args: 'def',
                                                            name: 'Sort 2',
                                                            options: [],
                                                            output: 'fed',
                                                            stdin: 'def',
                                                            weight: 1,
                                                        },
                                                    ],
                                                    program: 'abc',
                                                },
                                                hidden: true,
                                                id: 1,
                                                name: 'Simple test',
                                                type: 'io_test',
                                                weight: 2,
                                            },
                                            {
                                                data: {
                                                    inputs: [
                                                        {
                                                            args: 'abc',
                                                            id: 18,
                                                            name: 'Sort 3',
                                                            options: [
                                                                'regex',
                                                                'case',
                                                                'substring',
                                                            ],
                                                            output: 'ABC',
                                                            stdin: 'abc',
                                                            weight: 1,
                                                        },
                                                        {
                                                            args: 'def',
                                                            name: 'Sort 4',
                                                            options: [],
                                                            output: 'DEF',
                                                            stdin: 'def',
                                                            weight: 1,
                                                        },
                                                    ],
                                                    program: 'xyz',
                                                },
                                                hidden: false,
                                                id: 3,
                                                name: 'Advanced test',
                                                type: 'io_test',
                                                weight: 2,
                                            },
                                        ],
                                        rubric_row: {
                                            description:
                                                'The style of the code is conform to the styleguide.',
                                            header: 'Style',
                                            id: 1,
                                            items: [
                                                {
                                                    description:
                                                        'You have no style.You have no style.You have no style.You have no style.You have no style.',
                                                    header: 'Novice',
                                                    id: 3,
                                                    points: 1,
                                                },
                                                {
                                                    description:
                                                        "You don't know how to use some tools.You don't know how to use some tools.You don't know how to use some tools.You don't know how to use some tools.You don't know how to use some tools.",
                                                    header: 'Competent',
                                                    id: 2,
                                                    points: 2,
                                                },
                                                {
                                                    description:
                                                        'You know how to use some tools.You know how to use some tools.You know how to use some tools.You know how to use some tools.You know how to use some tools.',
                                                    header: 'Expert',
                                                    id: 1,
                                                    points: 3,
                                                },
                                            ],
                                        },
                                    },
                                    {
                                        autoTestSetId: 1,
                                        autoTestId: 1,
                                        id: 2,
                                        steps: [
                                            {
                                                data: {
                                                    program: './test_run',
                                                },
                                                hidden: false,
                                                id: 2,
                                                name: 'Test run',
                                                type: 'run_program',
                                                weight: 1,
                                            },
                                            {
                                                data: {
                                                    program: 'valgrind ./test_run',
                                                },
                                                hidden: true,
                                                id: 4,
                                                name: 'Valgrind',
                                                type: 'run_program',
                                                weight: 1,
                                            },
                                            {
                                                data: {
                                                    min_points: 4,
                                                    program: 'check_points ./test_run',
                                                },
                                                hidden: false,
                                                id: 5,
                                                name: 'Check points',
                                                type: 'check_points',
                                                weight: 0,
                                            },
                                            {
                                                data: {
                                                    program: 'get_points ./test_run',
                                                    regex: '(\\d+\\.?\\d*|\\.\\d+) points$',
                                                },
                                                hidden: false,
                                                id: 6,
                                                name: 'Get points',
                                                type: 'capture_points',
                                                weight: 1,
                                            },
                                        ],
                                        rubric_row: {
                                            description:
                                                'The code is strutured well and logical design choices were made.',
                                            header: 'Code structure',
                                            id: 3,
                                            items: [
                                                {
                                                    description:
                                                        "You don't know to use enter or space.You don't know to use enter or space.You don't know to use enter or space.You don't know to use enter or space.You don't know to use enter or space.",
                                                    header: 'Novice',
                                                    id: 9,
                                                    points: 1,
                                                },
                                                {
                                                    description:
                                                        'You know to use enter but not space.You know to use enter but not space.You know to use enter but not space.You know to use enter but not space.You know to use enter but not space.',
                                                    header: 'Competent',
                                                    id: 8,
                                                    points: 2.5,
                                                },
                                                {
                                                    description:
                                                        'You know to use enter and space.You know to use enter and space.You know to use enter and space.You know to use enter and space.You know to use enter and space.',
                                                    header: 'Expert',
                                                    id: 7,
                                                    points: 4,
                                                },
                                            ],
                                        },
                                    },
                                ],
                            },
                            {
                                id: 2,
                                stop_points: 0,
                                suites: [
                                    {
                                        autoTestSetId: 2,
                                        autoTestId: 1,
                                        id: 3,
                                        steps: [
                                            {
                                                data: {
                                                    inputs: [
                                                        {
                                                            args: '-a -b 1',
                                                            id: 13,
                                                            name: '-a -b 1',
                                                            options: [
                                                                'trailing_whitespace',
                                                                'substring',
                                                            ],
                                                            output: 'Python script',
                                                            stdin: 'Input input',
                                                            weight: 1,
                                                        },
                                                    ],
                                                    program: 'python python_runner.py',
                                                },
                                                hidden: false,
                                                id: 8,
                                                name: 'Python runner',
                                                type: 'io_test',
                                                weight: 1,
                                            },
                                        ],
                                        rubric_row: {
                                            description:
                                                'The documentation of the code is well written and complete.',
                                            header: 'Documentation',
                                            id: 2,
                                            items: [
                                                {
                                                    description:
                                                        'You typed a lot of wrong things.You typed a lot of wrong things.You typed a lot of wrong things.You typed a lot of wrong things.You typed a lot of wrong things.',
                                                    header: 'Novice',
                                                    id: 6,
                                                    points: 1,
                                                },
                                                {
                                                    description:
                                                        'You typed a lot of things, some wrong.You typed a lot of things, some wrong.You typed a lot of things, some wrong.You typed a lot of things, some wrong.You typed a lot of things, some wrong.',
                                                    header: 'Competent',
                                                    id: 5,
                                                    points: 1.5,
                                                },
                                                {
                                                    description:
                                                        'You typed a lot of things.You typed a lot of things.You typed a lot of things.You typed a lot of things.You typed a lot of things.',
                                                    header: 'Expert',
                                                    id: 4,
                                                    points: 2,
                                                },
                                            ],
                                        },
                                    },
                                ],
                            },
                        ],
                        setup_script: 'setup.py',
                        runs: [
                            {
                                id: 1,
                                results: [
                                    {
                                        id: 1,
                                        work: {
                                            id: 14,
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
                        ],
                    }),
                ).then(
                    () => {
                        delete loaders.tests[autoTestId];
                        return state.tests[autoTestId];
                    },
                    err => {
                        delete loaders.tests[autoTestId];
                        throw err;
                    },
                );
        }

        return loaders.tests[autoTestId];
    },

    async createAutoTestSet({ commit, dispatch, state }, { autoTestId }) {
        await dispatch('loadAutoTest', { autoTestId });
        const autoTest = state.tests[autoTestId];

        return axios
            .post(`/api/v1/auto_tests/${autoTestId}/sets/`)
            .then(
                ({ data }) => commit(types.UPDATE_AUTO_TEST, {
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

        return axios
            .delete(`/api/v1/auto_tests/${autoTestId}/sets/${setId}`)
            .then(
                () => commit(types.UPDATE_AUTO_TEST, {
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
            .then(
                () => commit(types.UPDATE_AUTO_TEST_SET, {
                    autoTestSet,
                    setProps,
                }),
            );
    },

    createAutoTestSuite({ commit }, { autoTestId, autoTestSet }) {
        const suites = autoTestSet.suites.concat(
            new AutoTestSuiteData(autoTestId, autoTestSet.id),
        );

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

    async loadAutoTestResult({ commit, dispatch, state }, { autoTestId, resultId }) {
        if (state.results[resultId] != null) {
            return state.results[resultId];
        }

        if (loaders.results[resultId] == null) {
            await dispatch('loadAutoTest', { autoTestId });
            const autoTest = state.tests[autoTestId];

            if (autoTest.runs.length === 0) {
                throw new Error('AutoTest has not been run yet.');
            }

            loaders.results[resultId] = axios
                .get(`/api/v1/auto_tests/${autoTestId}/runs/${autoTest.runs[0].id}/results/${resultId}`)
                .then(
                    ({ data }) => commit(types.SET_AUTO_TEST_RESULT, Object.assign(data, {
                        autoTest,
                    })),
                    // FIXME: remove
                    () => commit(types.SET_AUTO_TEST_RESULT, {
                        autoTest,
                        id: resultId,
                        setup_stdout: 'Setup script:\nSUCCESS!',
                        setup_stderr: '',
                        points_achieved: '3 / 15',
                        state: 'failed',
                        step_results: [
                            {
                                auto_test_step: autoTest.sets[0].suites[0].steps[0],
                                state: 'passed',
                                log: {
                                    steps: [
                                        {
                                            state: 'passed',
                                            stdout: 'ABC',
                                            stderr: 'WARNING: ...',
                                        },
                                        {
                                            state: 'passed',
                                            stdout: 'DEF',
                                            stderr: '',
                                        },
                                    ],
                                },
                            },
                            {
                                auto_test_step: autoTest.sets[0].suites[0].steps[1],
                                state: 'passed',
                                log: {
                                    steps: [
                                        {
                                            state: 'failed',
                                            stdout: 'ABC',
                                            stderr: 'ERROR: ...',
                                        },
                                        {
                                            state: 'passed',
                                            stdout: 'def',
                                            stderr: 'WARNING: ...',
                                        },
                                    ],
                                },
                            },
                            {
                                auto_test_step: autoTest.sets[0].suites[1].steps[0],
                                state: 'passed',
                                log: {
                                    stdout: 'passed!',
                                    stderr: '',
                                },
                            },
                            {
                                auto_test_step: autoTest.sets[0].suites[1].steps[1],
                                state: 'passed',
                                log: {
                                    stdout: 'passed!',
                                    stderr: '',
                                },
                            },
                            {
                                auto_test_step: autoTest.sets[0].suites[1].steps[2],
                                state: 'failed',
                                log: {
                                    stdout: 'Not enough points!!!',
                                    stderr: '',
                                },
                            },
                            {
                                auto_test_step: autoTest.sets[1].suites[0].steps[0],
                                state: 'running',
                                log: {
                                    steps: [
                                        {
                                            state: 'running',
                                            stdout: '',
                                            stderr: '',
                                        },
                                    ],
                                },
                            },
                        ],
                    }),
                ).then(
                    () => {
                        delete loaders.results[resultId];
                        return state.results[resultId];
                    },
                    err => {
                        delete loaders.results[resultId];
                        throw err;
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

        return axios
            .delete(`/api/v1/auto_tests/${autoTestId}/runs/${runId}`)
            .then(() => commit(types.UPDATE_AUTO_TEST, {
                autoTestId,
                autoTestProps: {
                    runs: autoTest.runs.filter(run => run.id !== runId),
                },
            }));
    },

    createFixtures({ commit }, { autoTestId, fixtures }) {
        return axios
            .patch(`/api/v1/auto_tests/${autoTestId}`, fixtures)
            .then(
                ({ data }) => commit(types.UPDATE_AUTO_TEST, {
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

        return axios[method](`/api/v1/auto_tests/${autoTestId}/fixtures/${fixture.id}/hide`)
            .then(
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
        autoTest.sets.forEach(
            set => {
                set.suites = set.suites.map(
                    suite => new AutoTestSuiteData(autoTest.id, set.id, suite),
                );
            },
        );

        Vue.set(state.tests, autoTest.id, autoTest);
    },

    [types.DELETE_AUTO_TEST](state, autoTestId) {
        state.tests[autoTestId].runs.forEach(run => {
            run.results.forEach(result => {
                Vue.delete(state.results, result.id);
            });
        });

        Vue.delete(state.tests, autoTestId);
    },

    [types.UPDATE_AUTO_TEST](state, { autoTestId, autoTestProps }) {
        const autoTest = state.tests[autoTestId];

        Object.entries(autoTestProps).forEach(
            ([k, v]) => Vue.set(autoTest, k, v),
        );
    },

    [types.UPDATE_AUTO_TEST_SET](state, { autoTestSet, setProps }) {
        Object.entries(setProps).forEach(
            ([k, v]) => Vue.set(autoTestSet, k, v),
        );
    },

    [types.DELETE_AUTO_TEST_SUITE](state, { autoTestSuite }) {
        Vue.set(autoTestSuite, 'deleted', true);
    },

    [types.SET_AUTO_TEST_RESULT](state, result) {
        const storeResult = new AutoTestResult(result);
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
