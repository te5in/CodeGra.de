/* SPDX-License-Identifier: AGPL-3.0-only */

const promises = [];

if (window.TextDecoder == null) {
    promises.push(
        import(/* webpackChunkName: 'text-encoding' */ 'text-encoding').then(({ TextDecoder }) => {
            window.TextDecoder = TextDecoder;
        }),
    );
}

if (window.URLSearchParams == null) {
    promises.push(
        import(/* webpackChunkName: 'url-search-params' */ 'url-search-params').then(
            ({ default: URLSearchParams }) => {
                window.URLSearchParams = URLSearchParams;
            },
        ),
    );
}

if (window.IntersectionObserver == null) {
    promises.push(import(/* webpackChunkName: 'intersection-observer' */ 'intersection-observer'));
}

promises.push(() => {
    Element.prototype.matches = Element.prototype.matches || Element.prototype.msMatchesSelector;
    Math.log10 = Math.log10 || (x => Math.log(x) / Math.LN10);

    if (!Object.prototype.hasOwnProperty.call(Object.prototype, 'fromEntries')) {
        // eslint-disable-next-line
        Object.defineProperty(Object.prototype, 'fromEntries', {
            value(iterable) {
                return [...iterable].reduce((obj, [key, val]) => {
                    obj[key] = val;
                    return obj;
                }, {});
            },
        });
    }

    // eslint-disable-next-line
    Array.prototype.findIndex =
        Array.prototype.findIndex ||
        function findIndex(callback) {
            if (this === null) {
                throw new TypeError('Array.prototype.findIndex called on null or undefined');
            } else if (typeof callback !== 'function') {
                throw new TypeError('callback must be a function');
            }

            const list = Object(this);
            // Makes sures is always has an positive integer as length.
            // eslint-disable-next-line
            const length = list.length >>> 0;
            // eslint-disable-next-line
            const thisArg = arguments[1];

            for (let i = 0; i < length; i++) {
                if (callback.call(thisArg, list[i], i, list)) {
                    return i;
                }
            }
            return -1;
        };

    Element.prototype.closest =
        Element.prototype.closest ||
        function closest(s) {
            let el = this;

            if (!document.documentElement.contains(el)) {
                return null;
            }

            for (
                ;
                el !== null && el.nodeType === Node.ELEMENT_NODE;
                el = el.parentElement || el.parentNode
            ) {
                if (el.matches(s)) {
                    return el;
                }
            }
            return null;
        };

    // eslint-disable-next-line
    String.prototype.startsWith =
        String.prototype.startsWith ||
        function startsWith(search, pos) {
            return this.substr(!pos || pos < 0 ? 0 : +pos, search.length) === search;
        };

    // eslint-disable-next-line
    String.prototype.endsWith =
        String.prototype.endsWith ||
        function endsWith(search, thisLen) {
            let len;
            if (thisLen === undefined || thisLen > this.length) {
                len = this.length;
            } else {
                len = thisLen;
            }
            return this.substring(len - search.length, len) === search;
        };
});

// eslint-disable-next-line
const polyFilled = Promise.all(promises);
export { polyFilled };
