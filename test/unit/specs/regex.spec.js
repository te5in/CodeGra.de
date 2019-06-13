import { ensurePythonRegexHasCaptureGroup as hasGroup } from '@/utils/regex';

describe('ensurePythonRegexHasCaptureGroup', () => {
    it('should be a function', () => {
        expect(typeof hasGroup).toBe('function');
    });

    it('should throw when regex has unbalanced parentheses', () => {
        expect(() => hasGroup('(')).toThrow();
        expect(() => hasGroup('((')).toThrow();
        expect(() => hasGroup(')')).toThrow();
        expect(() => hasGroup('))')).toThrow();
        expect(() => hasGroup('(()')).toThrow();
        expect(() => hasGroup('())')).toThrow();
        expect(() => hasGroup(')(')).toThrow();
        expect(() => hasGroup(')()')).toThrow();
        expect(() => hasGroup('(()()(())))')).toThrow();
    });

    it('should not throw when parentheses are correctly escaped', () => {
        expect(hasGroup('(\\()')).toBe(true);
        expect(hasGroup('(\\))')).toBe(true);
        expect(hasGroup('()\\(')).toBe(true);
        expect(hasGroup('()\\)')).toBe(true);
        expect(hasGroup('\\(()')).toBe(true);
        expect(hasGroup('\\)()')).toBe(true);
    });

    it('should recognize when the escape character itself is escaped', () => {
        expect(hasGroup('\\\\()')).toBe(true);
        expect(() => hasGroup('\\(\\\\)')).toThrow();
    });

    it('should throw when regex has no parentheses', () => {
        expect(() => hasGroup('')).toThrow();
        expect(() => hasGroup('abc')).toThrow();
        expect(() => hasGroup('[abc]*')).toThrow();
    });

    it('should throw when regex has only escaped parentheses', () => {
        expect(() => hasGroup('\\(')).toThrow();
        expect(() => hasGroup('\\)')).toThrow();
        expect(() => hasGroup('\\(\\)')).toThrow();
    });

    it('should throw when regex has only non-capturing parentheses', () => {
        expect(() => hasGroup('(?:abc)')).toThrow();
        expect(() => hasGroup('(?aabc)')).toThrow();
        expect(() => hasGroup('(?iabc)')).toThrow();
    });

    it('should accept a regex with at least one capture group', () => {
        expect(hasGroup('(abc)')).toBe(true);
        expect(hasGroup('((?:-\\s*)?1(?:\\.0*)?|0(?:\\.\\d*)?)')).toBe(true);
    });

    it('should accept a regex with a named capture group', () => {
        expect(hasGroup('(?P<name>abc)')).toBe(true);
        expect(hasGroup('(?P<name>(?:-\\s*)?1(?:\\.0*)?|0(?:\\.\\d*)?)')).toBe(true);
    });

    it.skip('should not accept a regex with a named capture group', () => {
        expect(() => hasGroup('(?P<>abc)')).toThrow();
        expect(() => hasGroup('(?Pabc)')).toThrow();
        expect(() => hasGroup('(?Pabc>abc)')).toThrow();
    });

    it('should accept a regex with nexted capture groups', () => {
        expect(hasGroup('(abc(def)ghi)')).toBe(true);
        expect(hasGroup('(?P<group>abc(def)ghi)')).toBe(true);
    });
});
