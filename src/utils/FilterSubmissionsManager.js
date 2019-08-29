/* SPDX-License-Identifier: AGPL-3.0-only */
import { cmpOneNull, cmpNoCase, nameOfUser, groupMembers } from '@/utils';

export function filterSubmissions(submissions, mine, userId, filter, callback = () => false) {
    const l = new Set();

    const filterAssignee = submissions.some(s => s.assignee && s.assignee.id === userId);

    return submissions.filter(item => {
        if (filterAssignee && mine && (item.assignee == null || item.assignee.id !== userId)) {
            if (!callback(item)) return false;
        } else if (!filter) {
            return true;
        }

        const terms = [
            nameOfUser(item.user).toLowerCase(),
            (item.grade || 0).toString(),
            item.formatted_created_at,
            nameOfUser(item.assignee).toLowerCase() || '-',
            ...groupMembers(item.user).map(n => n.toLowerCase()),
        ];
        const out = (filter || '')
            .toLowerCase()
            .split(' ')
            .every(word => terms.some(value => value.indexOf(word) >= 0));
        if (out) {
            l.add(item.user.id);
        }
        return out;
    });
}

export function sortSubmissions(a, b, sortBy) {
    const first = a[sortBy];
    const second = b[sortBy];

    const ret = cmpOneNull(first, second);
    if (ret !== null) {
        return ret;
    }

    if (sortBy === 'assignee') {
        return cmpNoCase(nameOfUser(first), nameOfUser(second));
    } else if (sortBy === 'user') {
        return cmpNoCase(nameOfUser(first), nameOfUser(second));
    } else if (sortBy === 'formatted_created_at' || sortBy === 'created_at') {
        const createdA = a.created_at;
        const createdB = b.created_at;

        const res = cmpOneNull(createdA, createdB);
        if (res !== null) return res;

        return cmpNoCase(createdA, createdB);
    } else if (sortBy === 'grade') {
        const firstF = parseFloat(first);
        const secondF = parseFloat(second);

        const ret2 = cmpOneNull(firstF, secondF);
        if (ret2 !== null) return ret2;

        const res = firstF - secondF;
        if (res) {
            return res;
        }
        return sortSubmissions(a, b, 'user');
    }

    return 0;
}

export default class FilterSubmissionsManager {
    constructor(currentSubmissionId, forceIncludeQuery, route, router) {
        this.curSubmissionId = currentSubmissionId;
        try {
            this.forceInclude = new Set(JSON.parse(forceIncludeQuery));
        } catch (_) {
            this.forceInclude = new Set();
        }
        this.$route = route;
        this.$router = router;
    }

    checkReally(sub) {
        if (this.forceInclude.has(sub.id)) {
            return true;
        }

        if (this.curSubmissionId === sub.id) {
            this.forceInclude.add(sub.id);
            this.$router.replace({
                query: Object.assign({}, this.$route.query, {
                    forceInclude: JSON.stringify([...this.forceInclude]),
                }),
            });
            return true;
        }
        return false;
    }

    filter(submissions, {
        mine, userId, filter, sortBy, asc,
    } = {}) {
        this.query = filter;
        if (submissions.length === 0) {
            return [];
        }
        const res = filterSubmissions(
            submissions,
            mine,
            userId,
            filter,
            this.checkReally.bind(this),
        ).sort((a, b) => sortSubmissions(a, b, sortBy));
        if (!asc) {
            res.reverse();
        }
        return res;
    }
}
