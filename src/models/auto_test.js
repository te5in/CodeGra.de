/* SPDX-License-Identifier: AGPL-3.0-only */
import Vue from 'vue';
// TODO: Remove the axios dependency and move the api requests to the store
import axios from 'axios';

import {
    deepCopy,
    getErrorMessage,
    getUniqueId,
    getProps,
    withOrdinalSuffix,
    safeDivide,
} from '@/utils';

export const FINISHED_STATES = new Set([
    'passed',
    'partial',
    'failed',
    'timed_out',
    'hidden',
    'skipped',
]);

export class AutoTestSuiteData {
    constructor(autoTestId, autoTestSetId, serverData = {}, actuallyFromServer) {
        this.autoTestSetId = autoTestSetId;
        this.autoTestId = autoTestId;
        this.trackingId = getUniqueId();

        this.id = null;
        this.steps = [];
        this.rubricRow = {};

        this.setFromServerData(serverData, actuallyFromServer);
    }

    setFromServerData(d, actuallyFromServer) {
        const trackingIds = this.getStepTrackingIds();

        const steps = (d.steps || []).map(step => {
            const ret = Object.assign(step, {
                trackingId: getProps(trackingIds, getUniqueId(), step.id),
                collapsed: true,
            });

            if (actuallyFromServer && step.type === 'check_points') {
                ret.data.min_points *= 100;
            }

            return ret;
        });

        Vue.set(this, 'id', d.id);
        Vue.set(this, 'steps', steps);
        Vue.set(this, 'rubricRow', d.rubric_row || {});
        Vue.set(
            this,
            'commandTimeLimit',
            getProps(d, UserConfig.autoTest.auto_test_max_command_time, 'command_time_limit'),
        );
        Vue.set(this, 'networkDisabled', getProps(d, true, 'network_disabled'));
    }

    getStepTrackingIds() {
        return this.steps.reduce((acc, step) => {
            acc[step.id] = step.trackingId;
            return acc;
        }, {});
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

    get url() {
        return `/api/v1/auto_tests/${this.autoTestId}/sets/${this.autoTestSetId}/suites/`;
    }

    // eslint-disable-next-line
    prepareStepForSaving(step) {
        const ret = {
            ...step,
            weight: Number(step.weight),
        };

        if (step.type === 'check_points') {
            ret.data = {
                ...step.data,
                min_points: step.data.min_points / 100,
            };
        }

        return ret;
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
                steps: this.steps.map(this.prepareStepForSaving),
                rubric_row_id: this.rubricRow.id,
                command_time_limit: Number(this.commandTimeLimit),
                network_disabled: getProps(this, true, 'networkDisabled'),
            })
            .then(
                res => {
                    this.setFromServerData(res.data, true);
                    return res;
                },
                err => {
                    const newErr = new Error('The category is not valid');
                    newErr.messages = {
                        general: [getErrorMessage(err)],
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
        step.trackingId = getUniqueId();
        this.steps.push(step);
    }

    // eslint-disable-next-line
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
            if (step.data.min_points < 0) {
                errs.push('The minimal percentage must be greater than 0.');
            } else if (step.data.max_points > 100) {
                errs.push('The mimimal percentage must be less than or equal to 100.');
            }
        } else if (step.type === 'custom_output') {
            if (!step.data.regex.match(/([^\\]|^)(\\\\)*\\f/)) {
                errs.push('The regular expression must contain at least one "\\f"');
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

export class AutoTestResult {
    constructor(result, autoTest) {
        this.id = result.id;
        this.submissionId = result.work_id;
        this.finished = false;

        this.update(result, autoTest);
    }

    update(result, autoTest) {
        this.createdAt = result.created_at;
        this.startedAt = result.started_at;
        this.pointsAchieved = result.points_achieved;

        this.updateState(result.state);
        this.updateStepResults(result.step_results, autoTest);
    }

    updateState(newState) {
        switch (newState) {
            case 'passed':
                this.state = 'done';
                break;
            default:
                this.state = newState;
                break;
        }

        this.finished = FINISHED_STATES.has(newState);
    }

    updateExtended(result, autoTest) {
        this.isFinal = result.final_result;
        this.setupStdout = result.setup_stdout;
        this.setupStderr = result.setup_stderr;
        this.approxWaitingBefore = result.approx_waiting_before;
        this.update(result, autoTest);
    }

    updateStepResults(steps, autoTest) {
        if (steps == null) {
            return;
        }

        const stepResults = steps.reduce((acc, step) => {
            acc[step.auto_test_step.id] = step;
            step.startedAt = step.started_at;

            if (step.log && step.log.steps) {
                step.log.steps.forEach(s => {
                    s.startedAt = s.started_at;
                });
            }
            return acc;
        }, {});

        const setResults = {};
        const suiteResults = {};

        const testFailed = this.state === 'failed' || this.state === 'timed_out';
        let setFailed = false;
        let totalAchieved = 0;
        let totalPossible = 0;

        autoTest.sets.forEach(set => {
            if (set.deleted) return;

            const setResult = {
                achieved: totalAchieved,
                possible: totalPossible,
                finished: false,
                set,
            };

            setResult.suiteResults = set.suites.map(suite => {
                if (suite.deleted) {
                    return null;
                }

                let suiteFailed = false;

                const suiteResult = {
                    achieved: 0,
                    possible: 0,
                    finished: false,
                    suite,
                };

                suiteResult.stepResults = suite.steps.map(step => {
                    let stepResult = stepResults[step.id];

                    if (!this.isFinal && step.hidden) {
                        stepResult = {
                            state: 'hidden',
                            log: null,
                        };
                    } else {
                        suiteResult.possible += step.weight;

                        if (stepResult == null) {
                            stepResult = {
                                state: 'not_started',
                                log: null,
                            };
                        }
                    }
                    stepResult.step = step;

                    if (step.type === 'check_points' && stepResult.state === 'failed') {
                        suiteFailed = true;
                    } else if (step.type === 'custom_output' && stepResult.state === 'passed') {
                        const points = stepResult.log.points;
                        if (points === 0) {
                            stepResult.state = 'failed';
                        } else if (points < 1) {
                            stepResult.state = 'partial';
                        }
                    }

                    suiteResult.achieved += getProps(stepResult, 0, 'achieved_points');
                    stepResult.finished = FINISHED_STATES.has(stepResult.state);

                    stepResults[step.id] = stepResult;
                    return stepResult;
                });

                suiteResult.percentage =
                    100 * safeDivide(suiteResult.achieved, suiteResult.possible, 0);
                suiteResult.finished = suiteResult.stepResults.every(s => s.finished);
                suiteResults[suite.id] = suiteResult;

                if (testFailed || setFailed || suiteFailed) {
                    suiteResult.finished = true;
                    suiteResult.stepResults.forEach(s => {
                        switch (s.state) {
                            case 'not_started':
                                s.state = 'skipped';
                                break;
                            case 'running':
                                s.state = 'failed';
                                break;
                            default:
                                break;
                        }
                    });
                }

                setResult.achieved += suiteResult.achieved;
                setResult.possible += suiteResult.possible;

                suiteResults[suite.id] = suiteResult;
                return suiteResult;
            });

            totalAchieved = setResult.achieved;
            totalPossible = setResult.possible;

            setResult.percentage = 100 * safeDivide(setResult.achieved, setResult.possible, 0);
            setResult.passed =
                setResult.percentage >= 100 * set.stop_points &&
                Object.values(setResults).every(prevSet => prevSet.passed);
            setResult.finished =
                setResult.suiteResults.every(s => s && s.finished) &&
                Object.values(setResults).every(prevSet => prevSet.finished);

            const achievedPerc = safeDivide(totalAchieved, totalPossible, 1);
            if (setResult.finished && achievedPerc < set.stop_points) {
                setFailed = true;
            }

            setResults[set.id] = setResult;
        });

        Vue.set(this, 'stepResults', stepResults);
        Vue.set(this, 'suiteResults', suiteResults);
        Vue.set(this, 'setResults', setResults);

        // Store a result per rubric row id for in the RubricViewer.
        Vue.set(
            this,
            'rubricResults',
            Object.values(suiteResults).reduce((acc, suiteResult) => {
                acc[suiteResult.suite.rubricRow.id] = suiteResult;
                return acc;
            }, {}),
        );
    }
}

export class AutoTestRun {
    constructor(run, autoTest) {
        this.id = run.id;
        this.createdAt = run.created_at;
        this.results = [];
        this.resultsByUser = {};
        this.update(run, autoTest);
    }

    update(run, autoTest) {
        this.setupStdout = run.setup_stdout;
        this.setupStderr = run.setup_stderr;

        if (run.results) {
            this.updateResults(run.results, autoTest);
        }
    }

    static makeNewResultArray(oldResults, newResults, autoTest) {
        // For each passed result, check if there is already a result with the
        // same id. If it exists, update that result and discard it from the
        // new results. Then create a new result for each result that wasn't
        // found. We do this to prevent the same user from appearing multiple
        // times in the results listing.
        const mapping = newResults.reduce((acc, r) => {
            acc[r.id] = r;
            return acc;
        }, {});

        const updated = oldResults.reduce((acc, r) => {
            if (r.id in mapping) {
                acc.push(r);
                r.update(mapping[r.id], autoTest);
                delete mapping[r.id];
            }
            return acc;
        }, []);

        return updated.concat(Object.values(mapping).map(r => new AutoTestResult(r, autoTest)));
    }

    updateResultsByUser(userId, newResults, autoTest) {
        Vue.set(
            this.resultsByUser,
            userId,
            AutoTestRun.makeNewResultArray(
                getProps(this.resultsByUser, [], userId),
                newResults,
                autoTest,
            ),
        );
    }

    updateResults(results, autoTest) {
        this.results = AutoTestRun.makeNewResultArray(this.results, results, autoTest);
    }

    findResultBySubId(submissionId) {
        let res = this.results.find(r => r.submissionId === submissionId);
        if (res == null) {
            Object.values(this.resultsByUser).find(results =>
                results.find(r => {
                    if (r.submissionId === submissionId) {
                        res = r;
                    }
                    return !!res;
                }),
            );
        }
        return res;
    }

    findResultById(resultId) {
        let res = this.results.find(r => r.id === resultId);
        if (res == null) {
            Object.values(this.resultsByUser).find(results =>
                results.find(r => {
                    if (r.id === resultId) {
                        res = r;
                    }
                    return !!res;
                }),
            );
        }
        return res;
    }

    setResultById(result) {
        let index = this.results.findIndex(res => res.id === result.id);
        if (index !== -1) {
            Vue.set(this.results, index, result);
        } else {
            const userId = Object.keys(this.resultsByUser).find(uId => {
                index = this.resultsByUser[uId].findIndex(r => r.id === result.id);
                return index !== -1;
            });
            Vue.set(this.resultsByUser[userId], index, result);
            Vue.set(this.resultsByUser, userId, this.resultsByUser[userId]);
        }
        return this;
    }
}
