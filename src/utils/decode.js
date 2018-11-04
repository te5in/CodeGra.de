/* This file contains code used to decode a buffer. It tries all possible
 * encodings, and fails if the encoding is not found.
 *
 * SPDX-License-Identifier: AGPL-3.0-only
 */

// Lazy cache that is used for decoders of the most common encodings.
const decoderCache = {};

// This should be ordered based on usage (the decoder of top five is cached and
// it will try to decode with these encodings from top to bottom). According to
// [0] this order should be quite okish.
//
// [0]: https://stackoverflow.com/questions/8509339/what-is-the-most-common-encoding-of-each-language
const encodings = [
    'utf-8', // This also covers ASCII
    'iso-8859-1', // 'windows-1252' or 'latin1'
    'windows-1251', /* According to Wikipedia widely used for Bulgarian, Serbian
                     * and Macedonian languages */
    'shift_jis', // Commenly used for the Japanese language.
    'iso-8859-2',
    'ibm866',
    'iso-8859-3',
    'iso-8859-4',
    'iso-8859-5',
    'iso-8859-6',
    'iso-8859-7',
    'iso-8859-8',
    'iso-8859-8-i',
    'iso-8859-10',
    'iso-8859-13',
    'iso-8859-14',
    'iso-8859-15',
    'iso-8859-16',
    'koi8-r',
    'koi8-u',
    'macintosh',
    'windows-874',
    'windows-1250',
    'windows-1253',
    'windows-1254',
    'windows-1255',
    'windows-1256',
    'windows-1257',
    'windows-1258',
    'x-mac-cyrillic',
    'gb18030',
    'hz-gb-2312',
    'big5',
    'euc-jp',
    'iso-2022-jp',
    'euc-kr',
    'utf-16be',
    'utf-16le',
];

// TODO: Find a way to determine the most popular encodings in a better way.
const popularEncodings = new Set(encodings.slice(0, 5));

function getOrCreateDecoder(encoding) {
    let decoder;
    if (decoderCache[encoding] == null) {
        decoder = new TextDecoder(encoding, { fatal: true });
        if (popularEncodings.has(encoding)) {
            decoderCache[encoding] = decoder;
        }
    } else {
        decoder = decoderCache[encoding];
    }
    return decoder;
}

export default function decodeBuffer(buffer) {
    for (let i = 0; i < encodings.length; i++) {
        const decoder = getOrCreateDecoder(encodings[i]);
        try {
            return decoder.decode(buffer);
        } catch (e) {
            // NOOP;
        }
    }
    throw new Error('Could not decode buffer');
}
