import { cmpOneNull, cmpNoCase } from '@/utils';

export function filterSubmissions(
    submissions,
    latest,
    mine,
    userId,
    filter,
    callback = () => false,
) {
    const l = new Set();
    let latestSubs = submissions;

    // BLAZE IT: R y a n C e l s i u s ° S o u n d s
    if (latest) {
        latestSubs = submissions.filter(item => {
            if (l.has(item.user.id)) {
                return callback(item);
            } else {
                l.add(item.user.id);
                return true;
            }
        });
    }

    const filterAssignee = latestSubs.some(s => s.assignee && s.assignee.id === userId);

    return latestSubs.filter(item => {
        if (filterAssignee && mine && (item.assignee == null || item.assignee.id !== userId)) {
            if (!callback(item)) return false;
        } else if (!filter) {
            return true;
        }

        const terms = [
            item.user.name.toLowerCase(),
            (item.grade || 0).toString(),
            item.formatted_created_at,
            item.assignee && item.assignee.name ? item.assignee.name.toLowerCase() : '-',
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
    if (sortBy === 'user' || sortBy === 'assignee') {
        const first = a[sortBy];
        const second = b[sortBy];

        const ret = cmpOneNull(first, second);
        if (ret !== null) return ret;

        return cmpNoCase(first.name, second.name);
    } else if (sortBy === 'created_at') {
        const first = a.formatted_created_at;
        const second = b.formatted_created_at;

        const ret = cmpOneNull(first, second);
        if (ret !== null) return ret;

        return cmpNoCase(first, second);
    } else if (sortBy === 'grade') {
        const first = a[sortBy];
        const second = b[sortBy];

        let ret = cmpOneNull(first, second);
        if (ret !== null) return ret;

        const firstF = parseFloat(first);
        const secondF = parseFloat(second);

        ret = cmpOneNull(firstF, secondF);
        if (ret !== null) return ret;

        return firstF - secondF;
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

    filter(submissions, latest, mine, userId, filter, sortBy) {
        this.query = filter;
        if (submissions.length === 0) {
            return [];
        }
        return filterSubmissions(
            submissions,
            latest,
            mine,
            userId,
            filter,
            this.checkReally.bind(this),
        ).sort((a, b) => sortSubmissions(a, b, sortBy));
    }
}
