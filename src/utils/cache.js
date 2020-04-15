// SPDX-License-Identifier: AGPL-3.0-only
import { UNSET_SENTINEL } from '@/constants';

export function makeCache(...keys) {
    const cache = Object.seal(Object.fromEntries(keys.map(key => [key, UNSET_SENTINEL])));

    return Object.freeze({
        _cache: cache,
        get(key, ifNotPresent) {
            if (this._cache[key] === UNSET_SENTINEL) {
                this._cache[key] = ifNotPresent();
            }
            return this._cache[key];
        },
    });
}
