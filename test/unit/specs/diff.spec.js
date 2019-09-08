import { getCapturePointsDiff, NEWLINE_CHAR } from '@/utils/diff';
import * as visualize from '@/utils/visualize';

describe('getCapturePointsDiff', () => {
    let mockVisul, mockSpan, txt1;

    beforeEach(() => {
        mockVisul = jest.fn(x => x);
        visualize.visualizeWhitespace = mockVisul;
        mockSpan = jest.fn((y, x) => `[${y}, "${x.replace(NEWLINE_CHAR, '_')}"]`)
        visualize.visualizeWhitespace = mockVisul;
        txt1 = 'Text\nNumber\t  One 11';
    })

    it('should work for equal strings', () => {
        const txt2 = txt1;
        const res = getCapturePointsDiff(txt1, txt2, [], true, mockSpan);
        expect(res).toEqual(txt2.split('\n'));
        expect(mockVisul).toBeCalled();
    });

    it('should work for simple additions', () => {
        const txt2 = 'Text\nNumber\t  Two 22';
        const res = getCapturePointsDiff(txt1, txt2, [], true, mockSpan);
        expect(res).toEqual(['Text', 'Number\t  [removed, "Two 22"][added, "One 11"]']);
    });

    it('should be possible to ignore trailing whitespace', () => {
        const txt2 = 'Hello\t\nText   \nNumber\t  Two 22';
        txt1 += '\t   ';
        const res = getCapturePointsDiff(txt1, txt2, ['trailing_whitespace'], true, mockSpan);
        expect(res).toEqual([
            '[removed, "Hello"][ignored, "\t"][removed, "_"]',
            'Text[ignored, "   "]',
            'Number\t  [removed, "Two 22"][added, "One 11"][ignored, "\t   "]',
        ]);

        const resIgnored = getCapturePointsDiff(txt1, txt2, ['trailing_whitespace'], false, mockSpan);
        expect(resIgnored).toEqual([
            '[removed, "Hello"][removed, "_"]',
            'Text',
            'Number\t  [removed, "Two 22"][added, "One 11"]',
        ]);
    });

    it('should be possible to ignore all case', () => {
        const txt2 = txt1.toLowerCase();
        const res = getCapturePointsDiff(txt1, txt2, ['case'], true, mockSpan);
        expect(res).toEqual(txt2.split('\n'));
    });

    it('should be possible to use substring', () => {
        const before = 'Hello this\nis some extra\nWOO';
        const after = 'JEE\n\n\nNICETRAILER';
        const middle = ' dit is een midden stuk! '
        const txt2 = `${before}${middle}!${after}`;
        const res = getCapturePointsDiff(middle + '?', txt2, ['substring'], true, mockSpan);
        expect(res).toEqual([
            '[ignored, "Hello this_"]',
            '[ignored, "is some extra_"]',
            '[ignored, "WOO"] dit is een midden stuk! [added, "?"][ignored, "!JEE_"]',
            '[ignored, "_"]',
            '[ignored, "_"]',
            '[ignored, "NICETRAILER"]'
        ]);

        const resIgnored = getCapturePointsDiff(middle + '?', txt2, ['substring'], false, mockSpan);
        expect(resIgnored).toEqual([' dit is een midden stuk! [added, "?"]']);
    });

    it('should work to ignore all whitespace', () => {
        txt1 = 'HelloD itiswhite space\n!?';
        const txt2 = 'Hello \n\tDit is whitespace\n!!';
        const res = getCapturePointsDiff(txt1, txt2, ['all_whitespace'], true, mockSpan);
        expect(res).toEqual([
            'Hello[ignored, " _"]',
            '[ignored, "\t"]D[ignored, " "]it[ignored, " "]is[ignored, " "]white[ignored, " "]space',
            '![removed, "!"][added, "?"]',
        ]);

        const resIgnored = getCapturePointsDiff(txt1, txt2, ['all_whitespace'], false, mockSpan);
        expect(resIgnored).toEqual([
            'Hello',
            'Ditiswhitespace',
            '![removed, "!"][added, "?"]',
        ]);
    });

    it('should work with substring and missing leading newlines', () => {
        txt1 = '\nHello';
        const txt2 = 'Hello';
        const res = getCapturePointsDiff(txt1, txt2, ['substring'], false, mockSpan);
        expect(res).toEqual([
            '[added, "_"]Hello'
        ]);
    });
});
