// SPDX-License-Identifier: AGPL-3.0-only
import Denque from 'denque';

// This function is weirdly enough not in Denque, so we simply add it
// ourselves. This is simply `peekAt`, but modified to set a value instead of
// returning it.
export default class Deque<T> extends Denque<T> {
    setAt(index: number, value: T): T | undefined {
        const len = this.length;
        let i = index;

        if (i >= len || i < -len) {
            return undefined;
        } else if (i < 0) {
            i += len;
        }

        const self: any = this;
        // eslint-disable-next-line
        i = (self._head + i) & self._capacityMask;

        // eslint-disable-next-line
        const old = self._list[i];
        // eslint-disable-next-line
        self._list[i] = value;
        return old;
    }
}
