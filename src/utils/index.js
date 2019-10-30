/* SPDX-License-Identifier: AGPL-3.0-only */
import moment from 'moment';
import * as assignmentState from '@/store/assignment-states';
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

export function formatGrade(grade) {
    const g = parseFloat(grade);
    return Number.isNaN(g) ? null : g.toFixed(2);
}

export function formatTimePart(num) {
    return `${num < 10 ? '0' : ''}${num}`;
}

export function toMaxNDecimals(num, n) {
    let str = num.toFixed(n);
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
    return first.toLocaleLowerCase().localeCompare(second.toLocaleLowerCase());
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

export function formatDate(date) {
    return moment
        .utc(date, moment.ISO_8601)
        .local()
        .format('YYYY-MM-DDTHH:mm');
}

export function readableFormatDate(date) {
    return moment
        .utc(date, moment.ISO_8601)
        .local()
        .format('YYYY-MM-DD HH:mm');
}

export function convertToUTC(timeStr) {
    return moment(timeStr, moment.ISO_8601)
        .utc()
        .format('YYYY-MM-DDTHH:mm');
}

export function parseWarningHeader(warningStr) {
    const arr = warningStr.split(' ');

    const code = parseFloat(arr[0]);
    const agent = arr[1];
    const text = arr
        .slice(2)
        .join(' ')
        .replace(/\\"/g, '"')
        .slice(1, -1);

    return { code, agent, text };
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
    else if (user.group) return `Group "${user.group.name}"`;
    else return user.name || '';
}

export function groupMembers(user) {
    if (!user || !user.group) return [];
    return user.group.members.map(nameOfUser);
}

export function userMatches(user, filter) {
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
    return sourceArr.map(line => {
        const { top, value } = highlight(language, line, true, state);

        state = top;
        return visualizeWhitespace(value);
    });
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
                if (!target[key]) {
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

// Divide a by b, or return dfl if b == 0.
export function safeDivide(a, b, dfl) {
    return b === 0 ? dfl : a / b;
}

export function deadlinePassed(assignment, now) {
    return now.isAfter(assignment.deadline);
}

export function canUploadWork(assignment, now) {
    const perms = assignment.course.permissions;

    if (!(perms.can_submit_own_work || perms.can_submit_others_work)) {
        return false;
    } else if (assignment.state === assignmentState.HIDDEN) {
        return false;
    } else if (deadlinePassed(assignment, now) && !perms.can_upload_after_deadline) {
        return false;
    } else {
        return true;
    }
}

export function canSeeGrade(assignment) {
    const perms = assignment.course.permissions;

    return assignment.state === assignmentState.DONE || perms.can_see_grade_before_open;
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
