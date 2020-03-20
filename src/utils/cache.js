import { UNSET_SENTINEL } from '@/constants';

export function makeCache(...keys) {
    const cache = Object.seal(
        Object.fromEntries(keys.map(key => [key, UNSET_SENTINEL])),
    );

    return Object.freeze({
        cache,
        get(key, ifNotPresent) {
            if (this.cache[key] === UNSET_SENTINEL) {
                this.cache[key] = ifNotPresent();
            }
            return this.cache[key];
        },
    });
}
