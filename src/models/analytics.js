/* SPDX-License-Identifier: AGPL-3.0-only */
import moment from 'moment';
import * as stat from 'simple-statistics';

import { store } from '@/store';
import {
    hasAttr,
    getProps,
    deepEquals,
    mapObject,
    filterObject,
    readableFormatDate,
    zip,
} from '@/utils';
import { makeCache } from '@/utils/cache';
import { defaultdict } from '@/utils/defaultdict';
import { NONEXISTENT } from '@/constants';

function averages(xs) {
    if (xs.length < 1) {
        return null;
    }

    return {
        mean: stat.mean(xs),
        median: stat.median(xs),
        mode: stat.mode(xs),
        stdev: xs.length < 2 ? 0 : stat.sampleStandardDeviation(xs),
    };
}

export class DataSource {
    static sourceName = '__base_data_source';

    static fromServerData(dataSource, workspace) {
        if (dataSource.name !== this.sourceName) {
            throw new TypeError('Invalid DataSource type');
        }
        if (!hasAttr(dataSource, 'data')) {
            throw new TypeError('Data source without data');
        }
        return new this(dataSource.data, workspace);
    }

    constructor(data, workspace) {
        if (this.constructor === DataSource) {
            throw new TypeError('DataSource should not be instantiated directly');
        }
        this.data = Object.freeze(data);
        this.workspace = workspace;
    }

    get assignment() {
        return getProps(this.workspace, null, 'assignment');
    }

    filter(subIds) {
        const data = filterObject(this.data, (_, id) => subIds.has(parseInt(id, 10)));
        return new this.constructor(data, this.workspace);
    }
}

export class RubricSource extends DataSource {
    static sourceName = 'rubric_data';

    constructor(data, workspace) {
        super(data, workspace);

        if (getProps(this.assignment, NONEXISTENT, 'rubric') === NONEXISTENT) {
            throw new Error('This assignment does not have a rubric');
        }

        this._cache = makeCache(
            'rubricItems',
            'rubricRowPerItem',
            'itemsPerCat',
            'meanPerCat',
            'stdevPerCat',
            'modePerCat',
            'medianPerCat',
            'nTimesFilledPerCat',
            'scorePerCatPerSubmission',
            'totalScorePerSubmission',
            'scorePerSubmissionPerCat',
            'ritItemsPerCat',
            'rirItemsPerCat',
            'ritPerCat',
            'rirPerCat',
        );

        this.updateItemPoints();

        Object.freeze(this);
    }

    updateItemPoints() {
        Object.values(this.data).forEach(items => {
            items.forEach(item => {
                if (!hasAttr(item, 'points')) {
                    const rubricItem = this.rubricItems[item.item_id];
                    item.points = item.multiplier * rubricItem.points;
                    Object.freeze(item);
                }
            });
            Object.freeze(items);
        });
    }

    get rubric() {
        return getProps(this.assignment, null, 'rubric');
    }

    get rowIds() {
        return this.rubric.rows.map(row => row.id);
    }

    get labels() {
        return this.rubric.rows.map(row => row.header);
    }

    get rubricItems() {
        return this._cache.get('rubricItems', () =>
            this.rubric.rows.reduce((acc, row) => {
                row.items.forEach(item => {
                    acc[item.id] = item;
                });
                return acc;
            }, {}),
        );
    }

    get rubricRowPerItem() {
        return this._cache.get('rubricRowPerItem', () =>
            this.rubric.rows.reduce((acc, row) => {
                row.items.forEach(item => {
                    acc[item.id] = row;
                });
                return acc;
            }, {}),
        );
    }

    get itemsPerCat() {
        return this._cache.get('itemsPerCat', () => {
            const rowPerItem = this.rubricRowPerItem;
            return Object.values(this.data).reduce((acc, items) => {
                items.forEach(item => {
                    const rowId = rowPerItem[item.item_id].id;
                    acc[rowId].push(item);
                });
                return acc;
            }, Object.fromEntries(this.rowIds.map(id => [id, []])));
        });
    }

    get nTimesFilledPerCat() {
        return this._cache.get('nTimesFilledPerCat', () =>
            mapObject(this.itemsPerCat, items => items.length),
        );
    }

    get meanPerCat() {
        return this._cache.get('meanPerCat', () =>
            mapObject(this.itemsPerCat, items => {
                if (items.length === 0) {
                    return null;
                } else {
                    const points = items.map(item => item.points);
                    return stat.mean(points);
                }
            }),
        );
    }

    get stdevPerCat() {
        return this._cache.get('stdevPerCat', () =>
            mapObject(this.itemsPerCat, items => {
                if (items.length < 1) {
                    return null;
                } else if (items.length === 1) {
                    return 0;
                } else {
                    const points = items.map(item => item.points);
                    return stat.sampleStandardDeviation(points);
                }
            }),
        );
    }

    get modePerCat() {
        return this._cache.get('modePerCat', () =>
            mapObject(this.itemsPerCat, items => {
                if (items.length === 0) {
                    return null;
                } else {
                    return stat.mode(items.map(item => item.points));
                }
            }),
        );
    }

    get medianPerCat() {
        return this._cache.get('medianPerCat', () =>
            mapObject(this.itemsPerCat, items => {
                if (items.length === 0) {
                    return null;
                } else {
                    return stat.median(items.map(item => item.points));
                }
            }),
        );
    }

    get scorePerCatPerSubmission() {
        return this._cache.get('scorePerCatPerSubmission', () => {
            const rowPerItem = this.rubricRowPerItem;
            return mapObject(this.data, items =>
                items.reduce((acc, item) => {
                    const rowId = rowPerItem[item.item_id].id;
                    acc[rowId] = item.points;
                    return acc;
                }, {}),
            );
        });
    }

    get totalScorePerSubmission() {
        return this._cache.get('totalScorePerSubmission', () =>
            mapObject(this.scorePerCatPerSubmission, scorePerCat =>
                stat.sum(Object.values(scorePerCat)),
            ),
        );
    }

    get ritItemsPerCat() {
        return this._cache.get('ritItemsPerCat', () => {
            const scoresPerSub = this.scorePerCatPerSubmission;
            const totalsPerSub = this.totalScorePerSubmission;

            return Object.entries(scoresPerSub).reduce((acc, [subId, scores]) => {
                Object.entries(scores).forEach(([rowId, score]) => {
                    acc[rowId].push([score, totalsPerSub[subId]]);
                });
                return acc;
            }, Object.fromEntries(this.rowIds.map(id => [id, []])));
        });
    }

    get rirItemsPerCat() {
        return this._cache.get('rirItemsPerCat', () =>
            mapObject(this.ritItemsPerCat, ritItems =>
                ritItems.map(([score, total]) => [score, total - score]),
            ),
        );
    }

    get ritPerCat() {
        return this._cache.get('ritPerCat', () =>
            mapObject(this.ritItemsPerCat, zipped => {
                if (zipped.length < 2) {
                    return null;
                }
                const ret = stat.sampleCorrelation(...zip(...zipped));
                return Number.isNaN(ret) ? null : ret;
            }),
        );
    }

    get rirPerCat() {
        return this._cache.get('rirPerCat', () =>
            mapObject(this.rirItemsPerCat, zipped => {
                if (zipped.length < 2) {
                    return null;
                }
                const ret = stat.sampleCorrelation(...zip(...zipped));
                return Number.isNaN(ret) ? null : ret;
            }),
        );
    }
}

export class InlineFeedbackSource extends DataSource {
    static sourceName = 'inline_feedback';

    constructor(data, workspace) {
        super(data, workspace);
        this._cache = makeCache('entryStats', 'entriesStdev');
        Object.freeze(this);
    }

    get entryStats() {
        return this._cache.get('entryStats', () => {
            const allEntries = Object.values(this.data);
            return averages(allEntries);
        });
    }
}

function createDataSource(data, workspace) {
    switch (data.name) {
        case 'rubric_data':
            return RubricSource.fromServerData(data, workspace);
        case 'inline_feedback':
            return InlineFeedbackSource.fromServerData(data, workspace);
        default:
            throw new TypeError('Invalid DataSource');
    }
}

const WORKSPACE_SUBMISSION_SERVER_PROPS = Object.freeze([
    'id',
    'assignee_id',
    'created_at',
    'grade',
]);

export class WorkspaceSubmission {
    static fromServerData(data) {
        const props = WORKSPACE_SUBMISSION_SERVER_PROPS.reduce((acc, prop) => {
            acc[prop] = data[prop];
            return acc;
        }, {});

        props.createdAt = moment.utc(data.created_at, moment.ISO_8601);

        return new WorkspaceSubmission(props);
    }

    constructor(props) {
        Object.assign(this, props);
        Object.freeze(this);
    }

    satisfies(filter) {
        const { minGrade, maxGrade, submittedAfter, submittedBefore, assignees } = filter;

        return (
            this.satisfiesGrade(minGrade, maxGrade) &&
            this.satisfiesDate(submittedAfter, submittedBefore) &&
            this.satisfiesAssignees(assignees)
        );
    }

    satisfiesGrade(minGrade, maxGrade) {
        // We do not want a submission to be in both filter A and
        // filter B if A has maxGrade=6 and B has minGrade=6, so we
        // need to check exclusively at one end. However, we need to be
        // inclusive at either 0 or the max grade for this assignment,
        // because otherwise we would drop some submissions. I chose
        // to be inclusive at the minGrade bound and exclusive at the
        // maxGrade bound because that feels more intuitive. This means
        // that a maxGrade of 9 will not contain submissions graded
        // exactly 9, but that a maxGrade of 10 _will_ include
        // submissions graded exactly 10.

        if ((minGrade != null || maxGrade != null) && this.grade == null) {
            return false;
        }
        if (minGrade != null && this.grade < minGrade) {
            return false;
        }
        if (maxGrade != null) {
            if (maxGrade === 10 && this.grade === 10) {
                return true;
            }
            if (this.grade >= maxGrade) {
                return false;
            }
        }
        return true;
    }

    satisfiesDate(submittedAfter, submittedBefore) {
        // Same as with the grade, but we do not have a maximum value to check for.

        if (submittedAfter != null && this.createdAt.isBefore(submittedAfter)) {
            return false;
        }
        if (submittedBefore != null && !this.createdAt.isBefore(submittedBefore)) {
            return false;
        }
        return true;
    }

    satisfiesAssignees(assignees) {
        if (assignees.length > 0) {
            return assignees.some(a => a.id === this.assignee_id);
        }
        return true;
    }
}

export class WorkspaceSubmissionSet {
    static fromServerData(data) {
        const subs = mapObject(data, ss => ss.map(WorkspaceSubmission.fromServerData));
        return new WorkspaceSubmissionSet(subs);
    }

    constructor(subs) {
        this.submissions = subs;
        this._cache = makeCache(
            'allSubmissions',
            'firstSubmission',
            'lastSubmission',
            'gradeStats',
            'submissionStats',
            'submissionsPerStudent',
            'submissionIds',
            'assigneeIds',
        );
        mapObject(this.submissions, Object.freeze);
        Object.freeze(this.submissions);
        Object.freeze(this);
    }

    get allSubmissions() {
        return this._cache.get('allSubmissions', () =>
            [].concat(...Object.values(this.submissions)),
        );
    }

    get firstSubmissionDate() {
        return this._cache.get('firstSubmission', () =>
            this.allSubmissions.reduce((first, sub) => {
                if (first == null || first.isAfter(sub.createdAt)) {
                    return sub.createdAt;
                } else {
                    return first;
                }
            }, null),
        );
    }

    get lastSubmissionDate() {
        return this._cache.get('lastSubmission', () =>
            this.allSubmissions.reduce((last, sub) => {
                if (last == null || last.isBefore(sub.createdAt)) {
                    return sub.createdAt;
                } else {
                    return last;
                }
            }, null),
        );
    }

    get submissionIds() {
        return this._cache.get('submissionIds', () => new Set(this.allSubmissions.map(s => s.id)));
    }

    get assigneeIds() {
        return this._cache.get('assigneeIds', () =>
            this.allSubmissions.reduce((acc, sub) => {
                if (sub.assignee_id != null) {
                    acc.add(sub.assignee_id);
                }
                return acc;
            }, new Set()),
        );
    }

    binSubmissionsBy(f) {
        return this.allSubmissions.reduce(
            (acc, sub) => {
                const bin = f(sub);
                if (bin != null) {
                    acc[f(sub)].push(sub);
                }
                return acc;
            },
            defaultdict(() => []),
        );
    }

    binSubmissionsByGrade(binSize = 1) {
        return this.binSubmissionsBy(sub => {
            const { grade } = sub;
            return grade == null ? null : Math.floor(grade / binSize);
        });
    }

    binSubmissionsByDate(range, binSize, binUnit) {
        const [start, end] = WorkspaceSubmissionSet.getDateRange(range);
        const binStep = moment.duration(binSize, binUnit).asMilliseconds();

        if (binStep === 0) {
            return {};
        }

        const getBin = d => {
            // We use unix timestamp for binning. Each bin starts at an integer
            // multiple of the bin size.
            // Correction term for the timezone offset.
            // utcOffset() is in seconds but we need milliseconds.
            const off = 60 * 1000 * d.utcOffset();
            return Math.floor((d.valueOf() + off) / binStep);
        };

        const binned = this.binSubmissionsBy(sub => {
            const { createdAt } = sub;

            if (
                (start != null && start.isAfter(createdAt)) ||
                (end !== null && end.isBefore(createdAt))
            ) {
                return null;
            }

            return getBin(createdAt);
        });

        const first = start == null ? Math.min(...Object.keys(binned)) : getBin(start);
        const last = end == null ? Math.max(...Object.keys(binned)) : getBin(end);

        const result = {};

        for (let i = first; i <= last; i++) {
            const binStart = i * binStep;
            result[binStart] = {
                start: binStart,
                end: binStart + binStep - 1,
                data: binned[i],
            };
        }

        return result;
    }

    static getDateRange(range) {
        let start;
        let end;

        if (range.length === 0) {
            return [null, null];
        } else {
            [start, end] = range.map(d => moment(d));
        }

        if (end == null) {
            end = start.clone();
        }

        return [
            start
                .local()
                .hours(0)
                .minutes(0)
                .seconds(0)
                .milliseconds(0),
            end
                .local()
                .hours(23)
                .minutes(59)
                .seconds(59)
                .milliseconds(999),
        ];
    }

    get submissionCount() {
        return this.allSubmissions.length;
    }

    get studentCount() {
        return Object.keys(this.submissions).length;
    }

    get gradeStats() {
        return this._cache.get('gradeStats', () => {
            const grades = this.allSubmissions.map(sub => sub.grade).filter(grade => grade != null);
            return averages(grades);
        });
    }

    get submissionStats() {
        return this._cache.get('submissionStats', () => {
            const subsPerStudent = Object.values(this.submissions)
                .filter(s => s.length > 0)
                .map(s => s.length);
            return averages(subsPerStudent);
        });
    }

    get submissionsPerStudent() {
        return this._cache.get('submissionsPerStudent', () => {
            const subsPerStudent = Object.values(this.submissions)
                .filter(s => s.length > 0)
                .map(s => s.length);
            return subsPerStudent.reduce(
                (acc, nSubs) => {
                    // XXX: This can probably be replaced with "acc[nSubs]++;"
                    // but I got a lot of errors, and at the time I thought they
                    // were related to that line. I don't get them anymore when
                    // using that expression, though... Needs further investigation!
                    const amt = acc[nSubs];
                    acc[nSubs] = amt + 1;
                    return acc;
                },
                defaultdict(() => 0),
            );
        });
    }

    filter(filter) {
        let filtered = filter.onlyLatestSubs ? this.getLatestSubmissions() : this.submissions;

        filtered = mapObject(filtered, subs => subs.filter(s => s.satisfies(filter)));

        filtered = filterObject(filtered, subs => subs.length > 0);

        return new WorkspaceSubmissionSet(filtered);
    }

    getLatestSubmissions() {
        return mapObject(this.submissions, subs => {
            const [first, ...rest] = subs;
            const latest = rest.reduce((a, b) => (a.createdAt.isAfter(b.createdAt) ? a : b), first);
            return latest == null ? [] : [latest];
        });
    }
}

const WORKSPACE_FILTER_DEFAULT_PROPS = Object.freeze({
    onlyLatestSubs: true,
    minGrade: null,
    maxGrade: null,
    submittedAfter: null,
    submittedBefore: null,
    assignees: [],
});

export class WorkspaceFilter {
    constructor(props) {
        Object.keys(props).forEach(key => {
            if (!hasAttr(WORKSPACE_FILTER_DEFAULT_PROPS, key)) {
                throw new Error(`Invalid filter: ${key}`);
            }
            this[key] = props[key];
        });

        Object.entries(WORKSPACE_FILTER_DEFAULT_PROPS).forEach(([key, defaultValue]) => {
            if (!hasAttr(this, key)) {
                this[key] = defaultValue;
            }
        });

        const maybeFloat = x => {
            const f = parseFloat(x);
            return Number.isNaN(f) ? null : f;
        };

        const maybeMoment = x => {
            const m = moment.utc(x, moment.ISO_8601);
            return m.isValid() ? m : null;
        };

        this.minGrade = maybeFloat(this.minGrade);
        this.maxGrade = maybeFloat(this.maxGrade);

        this.submittedAfter = maybeMoment(this.submittedAfter);
        this.submittedBefore = maybeMoment(this.submittedBefore);

        Object.defineProperty(this, '_cache', {
            value: makeCache('string'),
        });

        Object.freeze(this);
    }

    static get emptyFilter() {
        return new WorkspaceFilter(WORKSPACE_FILTER_DEFAULT_PROPS);
    }

    update(key, value) {
        return new WorkspaceFilter(Object.assign({}, this, { [key]: value }));
    }

    split(props) {
        const { minGrade, maxGrade, submittedAfter, submittedBefore } = this;

        const { latest, assignees } = props;
        const grade = parseFloat(props.grade);
        // moment(undefined) gives a valid moment, so we must convert it to
        // null first.
        const date = moment(props.date == null ? null : props.date);

        let result = [this];

        if (!Number.isNaN(grade)) {
            if (minGrade != null && minGrade >= grade) {
                throw new Error('Selected grade is less than or equal to the old "Min grade".');
            }
            if (maxGrade != null && maxGrade <= grade) {
                throw new Error('Selected grade is less than or equal to the old "Min grade".');
            }
            result = [].concat(
                ...result.map(f => [f.update('maxGrade', grade), f.update('minGrade', grade)]),
            );
        }

        if (date.isValid()) {
            if (submittedAfter != null && !submittedAfter.isBefore(date)) {
                throw new Error('Selected date is before the old "Submitted after".');
            }
            if (submittedBefore != null && !submittedBefore.isAfter(date)) {
                throw new Error('Selected date is after the old "Submitted before".');
            }
            result = [].concat(
                ...result.map(f => [
                    f.update('submittedBefore', date),
                    f.update('submittedAfter', date),
                ]),
            );
        }

        if (latest) {
            result = [].concat(
                ...result.map(f => [
                    f.update('onlyLatestSubs', false),
                    f.update('onlyLatestSubs', true),
                ]),
            );
        }

        if (assignees && assignees.length) {
            result = [].concat(...assignees.map(a => result.map(f => f.update('assignees', [a]))));
        }

        return result;
    }

    toString() {
        return this._cache.get('string', () => {
            const parts = [];

            if (this.onlyLatestSubs) {
                parts.push('Latest');
            } else {
                parts.push('All');
            }

            if (this.minGrade != null && this.maxGrade != null) {
                parts.push(`${this.minGrade} <= Grade < ${this.maxGrade}`);
            } else if (this.minGrade != null) {
                parts.push(`Grade >= ${this.minGrade}`);
            } else if (this.maxGrade != null) {
                parts.push(`Grade < ${this.maxGrade}`);
            }

            if (this.submittedAfter != null) {
                parts.push(`After ${readableFormatDate(this.submittedAfter)}`);
            }

            if (this.submittedBefore != null) {
                parts.push(`Before ${readableFormatDate(this.submittedBefore)}`);
            }

            parts.push(...this.assignees.map(a => a.name));

            return parts.join(', ');
        });
    }

    serialize() {
        const defaults = WorkspaceFilter.emptyFilter;
        const filter = filterObject(
            Object.assign({}, this),
            (val, key) => !deepEquals(val, defaults[key]),
        );
        if (filter.submittedAfter != null) {
            filter.submittedAfter = filter.submittedAfter.toISOString();
        }
        if (filter.submittedBefore != null) {
            filter.submittedBefore = filter.submittedBefore.toISOString();
        }
        if (filter.assignees != null) {
            filter.assignees = filter.assignees.map(a => a.id);
        }
        return filter;
    }

    static deserialize(data) {
        if (data.assignees != null) {
            data.assignees = data.assignees.map(id => store.getters['users/getUser'](id));
        }
        return new WorkspaceFilter(data);
    }
}

export class WorkspaceFilterResult {
    constructor(workspace, filter) {
        this.workspace = workspace;
        this.filter = filter;
        this.submissions = workspace.submissions.filter(filter);

        const subIds = this.submissions.submissionIds;
        this.dataSources = Object.freeze(mapObject(workspace.dataSources, ds => ds.filter(subIds)));

        Object.freeze(this);
    }

    get assignment() {
        return this.workspace.assignment;
    }

    getSource(sourceName) {
        return this.dataSources[sourceName];
    }
}

const WORKSPACE_SERVER_PROPS = Object.freeze(['id', 'assignment_id']);

export class Workspace {
    static fromServerData(workspace, sources) {
        const props = WORKSPACE_SERVER_PROPS.reduce((acc, prop) => {
            acc[prop] = workspace[prop];
            return acc;
        }, {});

        props.submissions = WorkspaceSubmissionSet.fromServerData(workspace.student_submissions);

        const self = new Workspace(props);
        const dataSources = workspace.data_sources.reduce((acc, srcName, i) => {
            const source = sources[i];
            if (source == null || source.name !== srcName) {
                throw new Error(`Did not receive data for source: ${srcName}`);
            }

            acc[srcName] = createDataSource(sources[i], self);
            return acc;
        }, {});
        // eslint-disable-next-line no-underscore-dangle
        self._setSources(dataSources);

        return self;
    }

    constructor(props, sources = null) {
        Object.assign(this, props);
        this.dataSources = {};
        Object.freeze(this);

        if (sources != null) {
            this._setSources(sources);
        }
    }

    _setSources(dataSources) {
        Object.assign(this.dataSources, dataSources);
        Object.freeze(this.dataSources);
    }

    hasSource(sourceName) {
        return hasAttr(this.dataSources, sourceName);
    }

    getSource(sourceName) {
        return this.dataSources[sourceName];
    }

    get assignment() {
        return store.getters['courses/assignments'][this.assignment_id];
    }

    filter(filters) {
        return filters.map(filter => new WorkspaceFilterResult(this, filter));
    }
}
