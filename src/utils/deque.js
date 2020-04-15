// SPDX-License-Identifier: AGPL-3.0-only
import Denque from 'denque';

// This function is weirdly enough not in Denque, so we simply add it
// ourselves. This is simply `peekAt`, but modified to set a value instead of
// returning it.
export default class Deque extends Denque {
    setAt(index, value) {
        const len = this.size();
        let i = index;

        if (i >= len || i < -len) {
            return undefined;
        } else if (i < 0) {
            i += len;
        }

        // eslint-disable-next-line
        i = (this._head + i) & this._capacityMask;

        // eslint-disable-next-line
        const old = this._list[i];
        // eslint-disable-next-line
        this._list[i] = value;
        return old;
    }
}
