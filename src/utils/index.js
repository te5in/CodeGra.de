/* SPDX-License-Identifier: AGPL-3.0-only */
import moment from 'moment';
import { getLanguage, highlight } from 'highlightjs';
import { visualizeWhitespace } from './visualize';

const reUnescapedHtml = /[&<>"'`]/g;
const reHasUnescapedHtml = RegExp(reUnescapedHtml.source);
/** Used to map characters to HTML entities. */
const htmlEscapes = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
    '`': '&#96;',
};
export function htmlEscape(inputString) {
    const string = typeof inputString === 'string' ? inputString : `${inputString}`;
    if (string && reHasUnescapedHtml.test(string)) {
        return string.replace(reUnescapedHtml, ent => htmlEscapes[ent]);
    }
    return string;
}

export function coerceToString(obj) {
    if (obj == null) return '';
    else if (typeof obj === 'string') return obj;
    return `${obj}`;
}

export function formatGrade(grade) {
    const g = parseFloat(grade);
    return Number.isNaN(g) ? null : g.toFixed(2);
}

export function formatTimePart(num) {
    return `${num < 10 ? '0' : ''}${num}`;
}

export function toMaxNDecimals(num, n) {
    if (num == null) {
        return null;
    }

    let str = num.toFixed(n);
    if (n === 0) {
        return str;
    }
    while (str[str.length - 1] === '0') {
        str = str.slice(0, -1);
    }
    if (str[str.length - 1] === '.') {
        str = str.slice(0, -1);
    }
    return str;
}

export function cmpOneNull(first, second) {
    if (first == null && second == null) {
        return 0;
    } else if (first == null) {
        return -1;
    } else if (second == null) {
        return 1;
    }
    return null;
}

export function cmpNoCase(first, second) {
    return coerceToString(first).localeCompare(coerceToString(second), undefined, {
        sensitivity: 'base',
    });
}

/**
 * Compare many 2-tuples of strings stopping at the first tuple that is not
 * equal. The `opts` param should be an array of arrays with two items.
 */
export function cmpNoCaseMany(...opts) {
    let res = 0;
    for (let i = 0; res === 0 && i < opts.length; ++i) {
        res = cmpNoCase(...opts[i]);
    }
    return res;
}

/**
 * Parse the given value as a boolean.
 * If it is a boolean return it, if it is 'false' or 'true' convert
 * that to its correct boolean value, otherwise return `dflt`.
 */
export function parseBool(value, dflt = true) {
    if (typeof value === 'boolean') return value;
    else if (value === 'false') return false;
    else if (value === 'true') return true;

    return dflt;
}

function toMoment(date) {
    if (moment.isMoment(date)) {
        return date.clone();
    } else {
        return moment.utc(date, moment.ISO_8601);
    }
}

export function formatDate(date) {
    return toMoment(date)
        .local()
        .format('YYYY-MM-DDTHH:mm');
}

export function readableFormatDate(date) {
    return toMoment(date)
        .local()
        .format('YYYY-MM-DD HH:mm');
}

export function convertToUTC(timeStr) {
    return moment(timeStr, moment.ISO_8601)
        .utc()
        .format('YYYY-MM-DDTHH:mm');
}

export function getProps(object, defaultValue, ...props) {
    let res = object;
    for (let i = 0; res != null && i < props.length; ++i) {
        res = res[props[i]];
    }
    if (res == null) {
        res = defaultValue;
    }
    return res;
}

export function setProps(object, value, ...props) {
    if (object == null) {
        throw new Error('Given object to set props on is null');
    }
    const lastProp = props.pop();
    let inner = object;

    for (let i = 0; i < props.length; ++i) {
        if (inner[props[i]] == null) {
            inner[props[i]] = {};
        }
        inner = inner[props[i]];
    }

    inner[lastProp] = value;
}

export class WarningHeader {
    static fromWarningStr(warningStr) {
        if (warningStr instanceof WarningHeader) {
            return warningStr;
        } else if (!warningStr) {
            return new WarningHeader([]);
        }

        let startIndex = 0;
        const res = [];
        const len = warningStr.length;

        function consume(part) {
            const arr = part.split(' ');

            const code = parseFloat(arr[0]);
            const agent = arr[1];
            const text = arr
                .slice(2)
                .join(' ')
                .replace(/\\(.)/g, '$1')
                .slice(1, -1);

            return { code, agent, text };
        }

        for (let i = 0, seenQuote = false; i < len; ++i) {
            const cur = warningStr.charAt(i);
            if (cur === '"') {
                if (seenQuote) {
                    res.push(consume(warningStr.slice(startIndex, i + 1)));
                    // Next char is a comma and then a space
                    startIndex = i + 3;
                    seenQuote = false;
                } else {
                    seenQuote = true;
                }
            } else if (cur === '\\') {
                // Skip next char
                i++;
            }
        }

        return new WarningHeader(res);
    }

    static fromResponse(response) {
        const warningStr = getProps(response, null, 'headers', 'warning');

        return WarningHeader.fromWarningStr(warningStr);
    }

    constructor(warnings) {
        this.messages = Object.freeze(warnings);
        Object.freeze(this);
    }

    merge(obj) {
        let other;
        if (other instanceof WarningHeader) {
            other = obj;
        } else if (obj.headers) {
            other = WarningHeader.fromResponse(obj);
        } else {
            other = WarningHeader.fromWarningStr(obj);
        }
        return new WarningHeader(this.messages.concat(other.messages));
    }
}

export function waitAtLeast(time, ...promises) {
    const timeout = new Promise(resolve => setTimeout(resolve, time));

    return Promise.all([timeout, ...promises]).then(vals => {
        if (promises.length === 1) {
            return vals[1];
        } else {
            return vals.slice(1);
        }
    });
}

export function getExtension(name) {
    const fileParts = name.split('.');
    return fileParts.length > 1 ? fileParts[fileParts.length - 1] : null;
}

export function last(arr) {
    return arr[arr.length - 1];
}

export function range(start, end) {
    if (end == null) {
        // eslint-disable-next-line
        end = start;
        // eslint-disable-next-line
        start = 0;
    }
    const len = end - start;
    const res = Array(len);
    for (let i = 0; i < len; ++i) {
        res[i] = start + i;
    }
    return res;
}

export function isDecimalNumber(val) {
    if (typeof val === 'number' || val instanceof Number) return true;
    else if (!(typeof val === 'string' || val instanceof String)) return false;

    let res = /^-?[1-9]\d*$/.test(val);
    res = res || /^0$/.test(val);
    res = res || /^-?[1-9]\d*\.\d+$/.test(val);
    res = res || /^-?0\.\d+$/.test(val);
    return res;
}

export function hashString(str) {
    let hash = 0;
    if (str.length === 0) return hash;

    for (let i = 0; i < str.length; i++) {
        const character = str.charCodeAt(i);
        hash = (hash << 5) - hash + character;
        hash &= hash; // Convert to 32bit integer
    }
    return Math.abs(hash << 0);
}

export function getOtherAssignmentPlagiarismDesc(item, index) {
    const assig = item.assignments[index];
    if (assig && assig.course.virtual) {
        return 'This submission was uploaded during running as part of an archive of old submissions.';
    }

    let desc = `This assignment was submitted to the assignment "${
        item.assignments[index].name
    }" of "${item.assignments[index].course.name}"`;

    if (item.submissions != null) {
        // These submissions are not yet submission object, so we don't have
        // `createdAt` property.
        const date = moment
            .utc(item.submissions[index].created_at, moment.ISO_8601)
            .local()
            .format('YYYY-MM-DD');
        desc = `${desc} on ${date}`;
    }

    return desc;
}

export function nameOfUser(user) {
    if (!user) return '';
    else if (user.readableName) return user.readableName;
    else if (user.group) return `Group "${user.group.name}"`;
    else return user.name || '';
}

export function groupMembers(user) {
    if (!user || !user.group) return [];
    return user.group.members.map(nameOfUser);
}

export function userMatches(user, filter) {
    // The given user might not be an actual user object, as this function is
    // also used by the plagiarism list.
    return [nameOfUser(user), ...groupMembers(user)].some(
        name => name.toLocaleLowerCase().indexOf(filter) > -1,
    );
}

export function highlightCode(sourceArr, language, maxLen = 5000) {
    if (sourceArr.length > maxLen) {
        return sourceArr.map(htmlEscape);
    }

    if (getLanguage(language) === undefined) {
        return sourceArr.map(htmlEscape).map(visualizeWhitespace);
    }

    let state = null;
    const lastLineIdx = sourceArr.length - 1;

    return sourceArr.map((line, idx) => {
        const { top, value } = highlight(language, line, true, state);

        state = top;
        // Make sure that if the last line is empty we emit this as an empty
        // line. We do this to make sure that our detection for trailing
        // newlines (or actually the absence of them) works correctly.
        if (idx === lastLineIdx && line === '') {
            return visualizeWhitespace(htmlEscape(line));
        }
        return visualizeWhitespace(value);
    });
}

export const getUniqueId = (() => {
    let id = 0;
    return () => id++;
})();

export function deepCopy(value, maxDepth = 10, depth = 1) {
    if (depth > maxDepth) {
        throw new Error('Max depth reached');
    }

    if (Array.isArray(value)) {
        return value.map(v => deepCopy(v, maxDepth, depth + 1));
    } else if (value && typeof value === 'object') {
        return Object.entries(value).reduce((res, [k, v]) => {
            res[k] = deepCopy(v, maxDepth, depth + 1);
            return res;
        }, {});
    } else {
        return value;
    }
}

export function capitalize(str) {
    if (str.length === 0) return str;
    return str[0].toUpperCase() + str.substr(1);
}

export function titleCase(str) {
    return str
        .split(' ')
        .map(capitalize)
        .join(' ');
}

export function withOrdinalSuffix(i) {
    const endsWith = i % 10;
    const mod100 = i % 100;
    const isTeen = mod100 >= 10 && mod100 < 20;
    let suffix = 'th';

    if (endsWith === 1 && !isTeen) {
        suffix = 'st';
    }
    if (endsWith === 2 && !isTeen) {
        suffix = 'nd';
    }
    if (endsWith === 3 && !isTeen) {
        suffix = 'rd';
    }

    return `${i}${suffix}`;
}

export function getErrorMessage(err) {
    let msg;

    if (err == null) {
        return '';
    } else if (err.response && err.response.data) {
        msg = err.response.data.message;
    } else if (err instanceof Error) {
        // eslint-disable-next-line
        console.error(err);
        msg = err.message;
    } else {
        msg = err.toString();
    }

    return msg || 'Something unknown went wrong';
}

// https://stackoverflow.com/questions/13405129/javascript-create-and-save-file
export function downloadFile(data, filename, contentType) {
    const file = new Blob([data], { type: contentType });
    if (window.navigator.msSaveOrOpenBlob) {
        // IE10+
        window.navigator.msSaveOrOpenBlob(file, filename);
    } else {
        const url = URL.createObjectURL(file);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        setTimeout(() => {
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }, 0);
    }
}

export function deepExtend(target, ...sources) {
    sources.forEach(source => {
        Object.entries(source).forEach(([key, val]) => {
            if (typeof val === 'object' && !Array.isArray(val)) {
                if (!Object.hasOwnProperty.call(target, key)) {
                    target[key] = {};
                }
                deepExtend(target[key], val);
            } else {
                target[key] = val;
            }
        });
    });
    return target;
}

export function deepExtendArray(target, ...sources) {
    sources.forEach(source => {
        Object.entries(source).forEach(([key, val]) => {
            if (typeof val === 'object') {
                if (!Object.hasOwnProperty.call(target, key)) {
                    target[key] = Array.isArray(val) ? [] : {};
                }
                deepExtend(target[key], val);
            } else {
                target[key] = val;
            }
        });
    });
    return target;
}

// Divide a by b, or return dfl if b == 0.
export function safeDivide(a, b, dfl) {
    return b === 0 ? dfl : a / b;
}

export function autoTestHasCheckpointAfterHiddenStep(autoTest) {
    let testHasHiddenStep = false;

    const sets = autoTest.sets;
    const nSets = sets.length;

    for (let i = 0; i < nSets; i++) {
        const set = sets[i];
        const suites = set.suites;
        const nSuites = suites.length;

        for (let j = 0; j < nSuites; j++) {
            const steps = suites[j].steps;
            const nSteps = steps.length;

            let suiteHasHiddenStep = false;

            for (let k = 0; k < nSteps; k++) {
                const step = steps[k];
                if (step.hidden) {
                    testHasHiddenStep = true;
                    suiteHasHiddenStep = true;
                }
                if (suiteHasHiddenStep && step.type === 'check_points') {
                    return true;
                }
            }
        }

        if (testHasHiddenStep && set.stop_points && i < nSets - 1) {
            return true;
        }
    }

    return false;
}

export function snakeToCamelCase(val) {
    return val.replace(/[-_]([a-z])/gi, inner => inner[1].toUpperCase());
}

/**
 * Get the `prop` from the first object in `objs` where `objs[i][prop]` is not
 * `null`.
 */
export function getNoNull(prop, ...objs) {
    for (let i = 0; i < objs.length; ++i) {
        if (objs[i] && objs[i][prop] != null) {
            return objs[i][prop];
        }
    }
    return null;
}

export function setXor(A, B) {
    return new Set([...A, ...B].filter(el => A.has(el) ^ B.has(el)));
}

export function numberToTimes(number) {
    if (typeof number !== 'number') {
        throw new Error('The given argument should be a number');
    }

    if (number === 1) {
        return 'once';
    } else if (number === 2) {
        return 'twice';
    } else {
        return `${number} times`;
    }
}

export function ensureArray(obj) {
    return Array.isArray(obj) ? obj : [obj];
}

export function mapObject(obj, f) {
    return Object.fromEntries(Object.entries(obj).map(([key, val]) => [key, f(val, key)]));
}
