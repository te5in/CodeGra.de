/* SPDX-License-Identifier: AGPL-3.0-only */
import fs from 'fs';

import { CGJunit } from '@/utils/junit';

function fixture(path) {
    return fs.readFileSync(`${__dirname}/../../../test_data/test_junit_xml/${path}`, null);
}

describe('CGJunit', () => {
    it('should work with a valid JUnit XML file', () => {
        const xml = fixture('valid.xml');
        const res = CGJunit.fromXml('1', xml);

        expect(res).toBeInstanceOf(CGJunit);
        expect(res.suites).toBeArray();
        expect(res.suites).not.toHaveLength(0);

        for (let suite of res.suites) {
            expect(suite.cases).toBeArray();
            expect(suite.cases).not.toHaveLength(0);
            expect(suite.successful + suite.failures + suite.errors).toBe(suite.totalTests);

            for (let c of suite.cases) {
                expect(c.state).not.toBe('unknown');

                if (c.state === 'success') {
                    expect(c.content).toBeNull();
                } else {
                    expect(c.content).toBeArray();
                    expect(c.content).not.toHaveLength(0);
                }

                expect(c.fontAwesomeIcon).toEqual(
                    expect.objectContaining({
                        icon: expect.any(String),
                        cls: expect.any(String),
                    }),
                );
            }
        }
    });

    it('should work when the state of a case is invalid', () => {
        const xml = fixture('valid_unknown_state.xml');
        const res = CGJunit.fromXml('1', xml);

        expect(res).toBeInstanceOf(CGJunit);
        expect(res.suites[0].cases[0].state).toBe('unknown');
    });

    it('should work when the the number of skipped tests is not given', () => {
        const xml = fixture('valid_no_skipped.xml');
        const res = CGJunit.fromXml('1', xml);

        expect(res).toBeInstanceOf(CGJunit);
        expect(res.suites[0].skipped).toBe(0);
    });

    it('should not work when the XML is invalid', () => {
        const xml = fixture('invalid_xml.xml');

        expect(() => {
            CGJunit.fromXml('1', xml);
        }).toThrow(/unclosed tag/i);

        const python = fixture('../test_submissions/hello.py');

        expect(() => {
            CGJunit.fromXml('1', python);
        }).toThrow(/text data outside of root node/i);
    });

    it('should not work when some attributes are missing', () => {
        const xml = fixture('invalid_missing_failures_attr.xml');

        expect(() => {
            CGJunit.fromXml('1', xml);
        }).toThrow();
    });

    it('should not work when the top level tag is not "testsuites"', () => {
        const xml = fixture('invalid_top_level_tag.xml');

        expect(() => {
            CGJunit.fromXml('1', xml);
        }).toThrow();
    });
});
