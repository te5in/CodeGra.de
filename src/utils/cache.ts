// SPDX-License-Identifier: AGPL-3.0-only
import { fromEntries, hasAttr, AssertionError } from './typed';
import { UNSET_SENTINEL } from '@/constants';

class Cache<T extends string> {
    private readonly _cache: Record<T, Object>;

    constructor(keys: T[]) {
        this._cache = Object.seal(
            fromEntries(keys.map(key => [key, UNSET_SENTINEL])),
        );
        Object.freeze(this);
    }

    get<V>(key: T, ifNotPresent: (key: T) => V): V {
        AssertionError.assert(hasAttr(this._cache, key));

        if (this._cache[key] === UNSET_SENTINEL) {
            this._cache[key] = ifNotPresent(key);
        }
        return this._cache[key] as V;
    }
}

export function makeCache<T extends string[]>(...keys: T): Cache<T[number]> {
    return new Cache(keys);
}
