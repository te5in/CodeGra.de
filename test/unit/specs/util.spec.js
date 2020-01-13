/* SPDX-License-Identifier: AGPL-3.0-only */
import moment from 'moment';

import {
    range,
    last,
    isDecimalNumber,
    formatGrade,
    formatDate,
    cmpOneNull,
    hashString,
    getExtension,
    waitAtLeast,
    highlightCode,
    nameOfUser,
    groupMembers,
    autoTestHasCheckpointAfterHiddenStep,
    safeDivide,
    parseWarningHeader,
    setProps,
    coerceToString,
    getNoNull,
} from '@/utils';

import * as assignmentState from '@/store/assignment-states';
import * as visualize from '@/utils/visualize';

import * as highlight from 'highlightjs';

jest.useFakeTimers();

describe('utils.js', () => {
    describe('range', () => {
        it('should work for zero length', () => {
            expect(range(2, 2)).toEqual([]);
        });

        it('should work for non zero length', () => {
            expect(range(2, 10)).toEqual([2, 3, 4, 5, 6, 7, 8, 9]);
        });

        it('should work for without begin', () => {
            expect(range(10)).toEqual([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]);
        });
    });

    describe('last', () => {
        it('should return a reference to the last item of the array', () => {
            const lastItem = { c: 'd' };
            expect(last([{ a: 'b' }, lastItem])).toBe(lastItem);
            expect(last([{ a: 'b' }, last])).not.toBe({ c: 'd' });
        });
    });

    describe('isDecimalNumber', () => {
        it('should accept numbers', () => {
            expect(isDecimalNumber(5)).toBe(true);
            expect(isDecimalNumber(-2)).toBe(true);
            expect(isDecimalNumber(11)).toBe(true);
        });

        it('should only accept numbers and strings', () => {
            expect(isDecimalNumber({})).toBe(false);
            expect(isDecimalNumber([])).toBe(false);
            expect(isDecimalNumber(new Number(5))).toBe(true);
            expect(isDecimalNumber(new String('5'))).toBe(true);
        });

        it('should work for some strings', () => {
            expect(isDecimalNumber('hello')).toBe(false);
            expect(isDecimalNumber('0x5')).toBe(false);
            expect(isDecimalNumber('08')).toBe(false);
            expect(isDecimalNumber('1.')).toBe(false);
            expect(isDecimalNumber('0.')).toBe(false);
            expect(isDecimalNumber('.50')).toBe(false);

            expect(isDecimalNumber('0')).toBe(true);
            expect(isDecimalNumber('0.8')).toBe(true);
            expect(isDecimalNumber('-0.8')).toBe(true);
            expect(isDecimalNumber('10')).toBe(true);
            expect(isDecimalNumber('-10')).toBe(true);
            expect(isDecimalNumber('-10.10')).toBe(true);
            expect(isDecimalNumber('10.10')).toBe(true);
        });
    });

    describe('formatGrade', () => {
        it('should work with normal numbers', () => {
            expect(formatGrade(5.5)).toBe('5.50');
            expect(formatGrade(5.55555)).toBe('5.56');
            expect(formatGrade(-5.55555)).toBe('-5.56');
        });

        it('should work with string numbers', () => {
            expect(formatGrade('5.5')).toBe('5.50');
            expect(formatGrade('5.55555')).toBe('5.56');
            expect(formatGrade('-5.55555')).toBe('-5.56');
            expect(formatGrade('11')).toBe('11.00');
        });

        it('zero should return a string', () => {
            expect(typeof formatGrade('0')).toBe('string');
            expect(formatGrade('0')).toBe('0.00');
        });

        it('non floats should return null', () => {
            expect(formatGrade('NO FLOAT')).toBe(null);
            expect(formatGrade(null)).toBe(null);
        });
    });

    describe('cmpOneNull', () => {
        it('should work with all permutations', () => {
            expect(cmpOneNull(null, null)).toBe(0);
            expect(cmpOneNull('not null', null)).toBe(1);
            expect(cmpOneNull(null, 'not null')).toBe(-1);
            expect(cmpOneNull('not null', 'not null')).toBe(null);
        });
    });

    describe('hashString', () => {
        it('should be a number', () => {
            expect(typeof hashString('hello')).toBe('number');
        });

        it('should be different for different strings', () => {
            expect(hashString('hello')).not.toBe(hashString('not hello'));
        });

        it('should work for empty strings', () => {
            expect(typeof hashString('')).toBe('number');
        });
    });

    describe('getExtension', () => {
        it('should work', () => {
            expect(getExtension('noextension')).toBe(null);
            expect(getExtension('hello.c')).toBe('c');
            expect(getExtension('hello.tar.gz')).toBe('gz');
        });
    });

    describe('waitAtLeast', () => {
        const time = 5000000;
        const obj1 = {n: 1};
        const obj2 = {n: 2};

        it('should work with one Promise', async () => {
            const fn = jest.fn();
            const promise = waitAtLeast(time, Promise.resolve(obj1));
            promise.then(fn);

            jest.advanceTimersByTime(250);
            expect(fn).not.toBeCalled();

            jest.advanceTimersByTime(time - 1);
            await expect(promise).resolves.toBe(obj1);
        });

        it('should work with multiple Promises', async () => {
            const fn = jest.fn();
            const promise = waitAtLeast(time, Promise.resolve(obj1), Promise.resolve(obj2));
            promise.then(fn);

            jest.advanceTimersByTime(250);
            expect(fn).not.toBeCalled();

            jest.advanceTimersByTime(time - 1);
            await expect(promise).resolves.toEqual([obj1, obj2]);
        });

        it('longest time should be used', async () => {
            const fn = jest.fn();
            const promise = waitAtLeast(time, new Promise(resolve => setTimeout(() => resolve(obj1), time + time)));
            promise.then(fn);

            jest.advanceTimersByTime(250);
            expect(fn).not.toBeCalled();

            jest.advanceTimersByTime(time - 1);
            expect(fn).not.toBeCalled();

            jest.advanceTimersByTime(time);
            await expect(promise).resolves.toBe(obj1);
        });
    });

    describe('highlightCode', () => {
        let mockVisul;
        let mockHighlight;
        let mockGetLang;
        let i = 0;

        beforeEach(() => {
            mockVisul = jest.fn(x => x);
            visualize.visualizeWhitespace = mockVisul;

            mockHighlight = jest.fn(function() {
                return {
                    value: Array.prototype.slice.call(arguments),
                    top: `STATE${++i}`,
                };
            });
            highlight.default.highlight = mockHighlight;
            mockGetLang = jest.spyOn(highlight.default, 'getLanguage');
        });

        afterEach(() => {
            i = 0;
            mockVisul.mockRestore();
            mockHighlight.mockRestore();
            mockGetLang.mockRestore();
        });

        it('should work without a language', () => {
            const data = Array(10).fill('<a>code line</a>')
            const res = Array(10).fill('&lt;a&gt;code line&lt;/a&gt;');
            expect(highlightCode(data)).toEqual(res);
            expect(mockVisul).toHaveBeenCalledTimes(data.length);
            expect(mockGetLang).toHaveBeenCalledTimes(1);
        });

        it('should work for very large arrays', () => {
            const data = Array(100).fill('hello');
            expect(highlightCode(data, 'NOT USED!', 99)).toEqual(data);
            // Should not be called for large files
            expect(mockVisul).not.toBeCalled();
            expect(mockGetLang).not.toBeCalled();
        });

        it('should work with a language', () => {
            const code = [
                'import os',
                '',
                'with open(os.path.join("dir", "file")) as f:',
                '\tprint(f.read())',
            ];
            const result = code.map(
                (x, idx) => ['python', x, true, idx ? `STATE${idx}` : null],
            );
            expect(highlightCode(code, 'python')).toEqual(result);
            expect(mockVisul).toHaveBeenCalledTimes(code.length);
            expect(mockGetLang).toHaveBeenCalledTimes(1);
        });
    });

    describe('nameOfUser', () => {
        const obj = {};

        it('should work for normal users', () => {
            expect(nameOfUser({
                name: obj
            })).toBe(obj);
        });

        it('should work for groups', () => {
            const groupName = `The name ${Math.random()}`;
            expect(nameOfUser({
                name: obj,
                group: { name: groupName },
            })).toEqual(`Group "${groupName}"`);
        });

        it('should work for empty objects', () => {
            expect(nameOfUser(null)).toEqual('');
            expect(nameOfUser({})).toEqual('');
        });

        it('should the `readableName` property if available', () => {
            const obj = {};
            expect(nameOfUser({ readableName: obj })).toBe(obj);
        });
    });

    describe('groupMembers', () => {
        it('should work for normal users', () => {
            expect(groupMembers({
                name: 'hello'
            })).toEqual([]);
        });

        it('should work for groups', () => {
            const name1 = Math.random();
            const name2 = Math.random();

            const groupName = `The name ${Math.random()}`;
            expect(groupMembers({
                name: 'HALLO',
                group: {
                    members: [
                        { name: name1 },
                        { name: name2 },
                    ],
                },
            })).toEqual([name1, name2]);
        });

        it('should work for empty objects', () => {
            expect(groupMembers(null)).toEqual([]);
            expect(groupMembers({})).toEqual([]);
        });
    });

    describe('autoTestHasCheckpointAfterHiddenStep', () => {
        function makeTest(sets) {
            return {
                sets,
            };
        }

        function makeSet(suites, stopPoints = 0) {
            return {
                suites,
                stop_points: stopPoints,
            };
        }

        function makeSuite(steps) {
            return {
                steps,
            };
        }

        function makeStep(type, hidden = false) {
            return {
                type,
                hidden,
            };
        }

        it('should return false when the test has no checkpoints', () => {
            expect(autoTestHasCheckpointAfterHiddenStep(makeTest([
                makeSet([
                    makeSuite([
                        makeStep('custom_output'),
                        makeStep('io_test', true),
                        makeStep('run_program', true),
                    ]),
                    makeSuite([
                        makeStep('custom_output'),
                        makeStep('io_test'),
                        makeStep('run_program', true),
                    ]),
                ]),
                makeSet([
                    makeSuite([
                        makeStep('custom_output', true),
                        makeStep('io_test', true),
                        makeStep('run_program'),
                    ]),
                    makeSuite([
                        makeStep('custom_output', true),
                        makeStep('io_test'),
                        makeStep('run_program'),
                    ]),
                ]),
            ]))).toBe(false);
        });

        it('should return false when the test has no hidden steps but does contain check_points steps', () => {
            expect(autoTestHasCheckpointAfterHiddenStep(makeTest([
                makeSet([
                    makeSuite([
                        makeStep('check_points'),
                        makeStep('custom_output'),
                        makeStep('io_test'),
                        makeStep('run_program'),
                    ]),
                    makeSuite([
                        makeStep('custom_output'),
                        makeStep('io_test'),
                        makeStep('run_program'),
                        makeStep('check_points'),
                    ]),
                ]),
                makeSet([
                    makeSuite([
                        makeStep('custom_output'),
                        makeStep('check_points'),
                        makeStep('io_test'),
                        makeStep('run_program'),
                    ]),
                    makeSuite([
                        makeStep('custom_output'),
                        makeStep('io_test'),
                        makeStep('check_points'),
                        makeStep('run_program'),
                    ]),
                ]),
            ]))).toBe(false);
        });

        it('should return false when the test has no hidden steps but does contain set checkpoints', () => {
            expect(autoTestHasCheckpointAfterHiddenStep(makeTest([
                makeSet([
                    makeSuite([
                        makeStep('custom_output'),
                        makeStep('io_test'),
                        makeStep('run_program'),
                    ]),
                    makeSuite([
                        makeStep('custom_output'),
                        makeStep('io_test'),
                        makeStep('run_program'),
                    ]),
                ], 0.5),
                makeSet([
                    makeSuite([
                        makeStep('custom_output'),
                        makeStep('io_test'),
                        makeStep('run_program'),
                    ]),
                    makeSuite([
                        makeStep('custom_output'),
                        makeStep('io_test'),
                        makeStep('run_program'),
                    ]),
                ]),
            ]))).toBe(false);
        });

        it('should return false when all check_points steps occur before the first hidden step in the same suite', () => {
            expect(autoTestHasCheckpointAfterHiddenStep(makeTest([
                makeSet([
                    makeSuite([
                        makeStep('check_points'),
                        makeStep('custom_output', true),
                        makeStep('io_test', true),
                        makeStep('run_program', true),
                    ]),
                ]),
            ]))).toBe(false);
        });

        it('should return false when a check_points step occurs after a suite with hidden steps', () => {
            expect(autoTestHasCheckpointAfterHiddenStep(makeTest([
                makeSet([
                    makeSuite([
                        makeStep('custom_output', true),
                        makeStep('io_test', true),
                        makeStep('run_program', true),
                    ]),
                    makeSuite([
                        makeStep('check_points'),
                    ]),
                ]),
            ]))).toBe(false);
        });

        it('should return false when all set checkpoints occur before the first hidden step', () => {
            expect(autoTestHasCheckpointAfterHiddenStep(makeTest([
                makeSet([
                    makeSuite([
                        makeStep('custom_output'),
                        makeStep('io_test'),
                        makeStep('run_program'),
                    ]),
                ], 0.5),
                makeSet([
                    makeSuite([
                        makeStep('custom_output', true),
                        makeStep('io_test'),
                        makeStep('run_program', true),
                    ]),
                ]),
            ]))).toBe(false);
        });

        it('should return false when a set checkpoint of the only set happens after hidden steps', () => {
            expect(autoTestHasCheckpointAfterHiddenStep(makeTest([
                makeSet([
                    makeSuite([
                        makeStep('custom_output', true),
                        makeStep('io_test', true),
                        makeStep('run_program'),
                    ]),
                ], 1.0),
            ]))).toBe(false);
        });

        it('should return false when a set checkpoint of the last set happens after hidden steps in a previous set', () => {
            expect(autoTestHasCheckpointAfterHiddenStep(makeTest([
                makeSet([
                    makeSuite([
                        makeStep('custom_output', true),
                        makeStep('io_test', true),
                        makeStep('run_program'),
                    ]),
                ]),
                makeSet([
                    makeSuite([
                        makeStep('custom_output'),
                        makeStep('io_test'),
                        makeStep('run_program'),
                    ]),
                ], 1.0),
            ]))).toBe(false);
        });

        it('should return false when a set checkpoint of the last set happens after hidden steps in the same set', () => {
            expect(autoTestHasCheckpointAfterHiddenStep(makeTest([
                makeSet([
                    makeSuite([
                        makeStep('custom_output'),
                        makeStep('io_test'),
                        makeStep('run_program'),
                    ]),
                ]),
                makeSet([
                    makeSuite([
                        makeStep('custom_output', true),
                        makeStep('io_test', true),
                        makeStep('run_program'),
                    ]),
                ], 1.0),
            ]))).toBe(false);
        });

        it('should return true when a check_points step happens after hidden steps in the same suite', () => {
            expect(autoTestHasCheckpointAfterHiddenStep(makeTest([
                makeSet([
                    makeSuite([
                        makeStep('custom_output', true),
                        makeStep('io_test', true),
                        makeStep('run_program'),
                        makeStep('check_points'),
                    ]),
                ]),
            ]))).toBe(true);
        });

        it('should return true when a set checkpoint happens after hidden steps', () => {
            expect(autoTestHasCheckpointAfterHiddenStep(makeTest([
                makeSet([
                    makeSuite([
                        makeStep('custom_output', true),
                        makeStep('io_test', true),
                        makeStep('run_program'),
                    ]),
                ], 1.0),
                makeSet([
                    makeSuite([
                        makeStep('custom_output'),
                    ]),
                ]),
            ]))).toBe(true);
        });
    });

    describe('safeDivide', () => {
        it('should work when both are not 0', () => {
            expect(safeDivide(4, 10, {})).toBe(4 / 10);
        });
        it('should work when both are 0', () => {
            const res = {};
            expect(safeDivide(0, 0, res)).toBe(res);
        });
        it('should work when one is 0', () => {
            const res = {};
            expect(safeDivide(10, 0, res)).toBe(res);
            expect(safeDivide(0, 10, res)).toBe(0);
        });
    });

    describe('parseWarningHeader', () => {
        it('should work for simple single warnings', () => {
            expect(parseWarningHeader('14 C "Hello warning"')).toEqual([{
                code: 14,
                agent: 'C',
                text: 'Hello warning',
            }]);
        });

        it('should work for multiple simple warnings', () => {
            expect(parseWarningHeader('14 C "Hello warning", 15 C "W2"')).toEqual([{
                code: 14,
                agent: 'C',
                text: 'Hello warning',
            }, {
                code: 15,
                agent: 'C',
                text: 'W2',
            }]);
        });

        it('should work for difficult warnings', () => {
            const warningStr = '14 C_C ",\\"WARN\\\\ING\\\\", 14 C ",,"';
            expect(parseWarningHeader(warningStr)).toEqual([{
                code: 14,
                agent: 'C_C',
                text: ',"WARN\\ING\\',
            }, {
                code: 14,
                agent: 'C',
                text: ',,',
            }]);
        });
    });

    describe('setProps', () => {
        it('should work when the key is not there yet', () => {
            let obj = {};
            let value = {};
            setProps(obj, value, '1', '2', '3', '4');
            expect(obj).toEqual({
                1: {
                    2: {
                        3: {
                            4: value,
                        }
                    }
                }
            })
            expect(obj[1][2][3][4]).toBe(value);
        });

        it('should work when a part of the path is there', () => {
            let obj = {};
            let value = {1: { 2: { }}};
            setProps(obj, value, '1', '2', '3', '4');
            expect(obj).toEqual({
                1: {
                    2: {
                        3: {
                            4: value,
                        }
                    }
                }
            })
            expect(obj[1][2][3][4]).toBe(value);
        });

        it('should throw when the given object is null', () => {
            expect(() => setProps(null, 5, 1)).toThrow(Error);
        });
    });

    describe('coerceToString', () => {
        it('should work for strings', () => {
            expect(coerceToString('abc')).toBe('abc');
        });

        it('should work for null', () => {
            expect(coerceToString(null)).toBe('');
        });

        it('should work for objects', () => {
            expect(coerceToString(true)).toBe('true');

            expect(coerceToString({})).toBe('[object Object]');
            expect(coerceToString({ toString() { return 'abc'; }})).toBe('abc');
        });

        it('should work for numbers', () => {
            expect(coerceToString(-1)).toBe('-1');
            expect(coerceToString(15.555)).toBe('15.555');
            expect(coerceToString(0)).toBe('0');
            expect(coerceToString(1)).toBe('1');
        });
    });

    describe('getNoNull', () => {
        const obj1 = {};
        const obj2 = {};

        it('should work when it is in the first obj', () => {
            expect(getNoNull('a', {a: obj1}, {a: obj2})).toBe(obj1);
        });
        it('should work when it is not the first obj', () => {
            expect(getNoNull('b', {a: obj1}, null, {b: obj2})).toBe(obj2);
        });
        it('should return null if it is not found', () => {
            expect(getNoNull('c', {a: obj1}, null, {b: obj2})).toBe(null);
        });
    });
});
