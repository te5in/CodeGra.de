/* SPDX-License-Identifier: AGPL-3.0-only */
import fs from 'fs';

import decodeBuffer from '@/utils/decode.js';

describe('decoder.js', () => {
    describe('decodeBuffer', () => {
        it('should be a function', () => {
            expect(typeof decodeBuffer).toBe('function');
        });

        it('should work with a utf8 file', () => {
            const buffer = fs.readFileSync(`${__dirname}/../test_data/utf8.txt`, null);
            expect(decodeBuffer(buffer)).toBe('utf-8 file\n');
        });

        it('should work with a latin1 file', () => {
            const buffer = fs.readFileSync(`${__dirname}/../test_data/latin1.txt`, null);
            expect(decodeBuffer(buffer)).toBe('latin1 filé\n');
        });

        it('should work with force', () => {
            const buffer = fs.readFileSync(`${__dirname}/../test_data/latin1.txt`, null);
            expect(decodeBuffer(buffer, true)).toBe('latin1 fil�\n');
            expect(decodeBuffer(buffer, true)).toBe('latin1 fil�\n');
        });

        it('should throw on a binary file', () => {
            const buffer = fs.readFileSync(`${__dirname}/../test_data/binary`, null);
            expect(() => decodeBuffer(buffer)).toThrow();
        });

        it('should work reusing a utf-8 buffer', () => {
            const buffer = fs.readFileSync(`${__dirname}/../test_data/utf8.txt`, null);
            expect(decodeBuffer(buffer)).toBe('utf-8 file\n');
            expect(decodeBuffer(buffer)).toBe('utf-8 file\n');
        });
    });
});
