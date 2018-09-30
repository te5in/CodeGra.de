import { range, last, visualizeWhitespace, nSpaces, nTabs, isDecimalNumber } from '@/utils';

describe('visualizeWhitespace in utils.js', () => {
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


describe('range in utils.js', () => {
    it('should work for zero length', () => {
        expect(range(2, 2)).toEqual([]);
    });

    it('should work for non zero length', () => {
        expect(range(2, 10)).toEqual([2, 3, 4, 5, 6, 7, 8, 9]);
    });
});

describe('last in util.js', () => {
    it('should return a reference to the last item of the array', () => {
        const lastItem = { c: 'd' };
        expect(last([{ a: 'b' }, lastItem])).toBe(lastItem);
        expect(last([{ a: 'b' }, last])).not.toBe({ c: 'd' });
    });
});

describe('isDecimalNumber in util.js', () => {
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
