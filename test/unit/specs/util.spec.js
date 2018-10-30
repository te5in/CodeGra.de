/* SPDX-License-Identifier: AGPL-3.0-only */
import {
    range,
    last,
    visualizeWhitespace,
    nSpaces,
    nTabs,
    isDecimalNumber,
    formatGrade,
    cmpOneNull,
    hashString,
    getExtension,
    waitAtLeast,
} from '@/utils';

jest.useFakeTimers();

describe('utils.js', () => {
    describe('visualizeWhitespace', () => {
        it('should be a function', () => {
            expect(typeof visualizeWhitespace).toBe('function');
        });

        it('should work with an empty line', () => {
            expect(visualizeWhitespace('')).toBe('');
        });

        it('should work without spaces', () => {
            const text = '<span class="nospaces wwee">hellonospaceshere</span>';
            expect(visualizeWhitespace(text)).toBe(text);
        });

        it('should work with a single space', () => {
            const text = '<span class="single space">hello space</span>';
            const res = `<span class="single space">hello${nSpaces(1)}space</span>`;
            expect(visualizeWhitespace(text)).toBe(res);
        });

        it('should work with a large amount of spaces', () => {
            const spaces = Array(18).join(' ');
            const text = `<span class="many space">hello${spaces}space</span>`;
            const res = `<span class="many space">hello${nSpaces(1)}${nSpaces(8)}${nSpaces(8)}space</span>`;
            expect(visualizeWhitespace(text)).toBe(res);
        });

        it('should work with a single tab', () => {
            const text = '<span class="single tab">hello\ttab</span>';
            const res = `<span class="single tab">hello${nTabs(1)}tab</span>`;
            expect(visualizeWhitespace(text)).toBe(res);
        });

        it('should work with a large amount of tabs', () => {
            const tabs = Array(18).join('\t');
            const text = `<span class="many tab">hello${tabs}tab</span>`;
            const res = `<span class="many tab">hello${nTabs(1)}${nTabs(4)}${nTabs(4)}${nTabs(4)}${nTabs(4)}tab</span>`;
            const out = visualizeWhitespace(text);

            expect(out).toBe(res);
            expect(out.split('<wbr>').length).toBe(18);
        });
    });

    describe('range', () => {
        it('should work for zero length', () => {
            expect(range(2, 2)).toEqual([]);
        });

        it('should work for non zero length', () => {
            expect(range(2, 10)).toEqual([2, 3, 4, 5, 6, 7, 8, 9]);
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
});
