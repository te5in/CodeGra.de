/* SPDX-License-Identifier: AGPL-3.0-only */

export default function decodeBuffer(buffer, force = false) {
    const fatal = !force;
    try {
        return new TextDecoder('utf8', { fatal }).decode(buffer);
    } catch (e) {
        if (new Int8Array(buffer).includes(0)) {
            throw new Error('Binary file detected');
        }
        return new TextDecoder('latin1', { fatal }).decode(buffer);
    }
}
