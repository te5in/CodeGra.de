/* SPDX-License-Identifier: AGPL-3.0-only */
import moment from 'moment';
import * as stat from 'simple-statistics';

import { store } from '@/store';
// eslint-ignore-next-line
import {
    getProps,
    mapObject,
    filterObject,
    readableFormatDate,
    zip,
} from '@/utils';
import { makeCache } from '@/utils/cache';
import { defaultdict } from '@/utils/defaultdict';

function dropNull(xs) {
    return xs.filter(x => x != null);
}

export class DataSource {
    static sourceName = '__base_data_source';

    static fromServerData() {
        throw new Error('Not implemented');
    }

    static checkType(dataSource) {
        if (dataSource.name !== this.sourceName) {
            throw new TypeError('Invalid DataSource type');
        }
    }

    constructor(data, workspace) {
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

    static fromServerData(dataSource, workspace) {
        this.checkType(dataSource);
        return new RubricSource(dataSource.data, workspace);
    }

    constructor(data, workspace) {
        super(data, workspace);

        if (getProps(workspace, null, 'assignment', 'rubric') == null) {
            throw new Error('This assignment does not have a rubric');
        }

        this._cache = makeCache(
            'rubricItems',
            'rubricRowPerItem',
            'itemsPerCat',
            'meanPerCat',
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
                if (!Object.hasOwnProperty.call(item, 'points')) {
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
            return Object.values(this.data).reduce(
                (acc, items) => {
                    items.forEach(item => {
                        const rowId = rowPerItem[item.item_id].id;
                        acc[rowId].push(item);
                    });
                    return acc;
                },
                Object.fromEntries(this.rowIds.map(id => [id, []])),
            );
        });
    }

    get nTimesFilledPerCat() {
        return this._cache.get('nTimesFilledPerCat', () =>
            mapObject(this.itemsPerCat, items => items.length),
        );
    }

    mapItemsPerCat(f, skipEmpty = false) {
        return mapObject(this.itemsPerCat, (items, rowId) => {
            if (skipEmpty && items.length === 0) {
                return [];
            }
            return f(items, rowId);
        });
    }

    get meanPerCat() {
        return this._cache.get('meanPerCat', () =>
            this.mapItemsPerCat(items => stat.mean(items.map(item => item.points)), true),
        );
    }

    get modePerCat() {
        return this._cache.get('modePerCat', () =>
            this.mapItemsPerCat(items => stat.mode(items.map(item => item.points)), true),
        );
    }

    get medianPerCat() {
        return this._cache.get('medianPerCat', () =>
            this.mapItemsPerCat(items => stat.median(items.map(item => item.points)), true),
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

            return Object.entries(scoresPerSub).reduce(
                (acc, [subId, scores]) => {
                    Object.entries(scores).forEach(([rowId, score]) => {
                        acc[rowId].push([score, totalsPerSub[subId]]);
                    });
                    return acc;
                },
                Object.fromEntries(this.rowIds.map(id => [id, []])),
            );
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
                // eslint-disable-next-line no-unused-vars
                const filtered = zipped.filter(([_, total]) => total !== 0);
                if (filtered.length < 10) {
                    return null;
                }
                return stat.sampleCorrelation(...zip(...filtered));
            }),
        );
    }

    get rirPerCat() {
        return this._cache.get('rirPerCat', () =>
            mapObject(this.rirItemsPerCat, zipped => {
                // eslint-disable-next-line no-unused-vars
                const filtered = zipped.filter(([_, total]) => total !== 0);
                if (filtered.length < 10) {
                    return null;
                }
                return stat.sampleCorrelation(...zip(...filtered));
            }),
        );
    }
}

export class InlineFeedbackSource extends DataSource {
    static sourceName = 'inline_feedback';

    static fromServerData(dataSource, workspace) {
        this.checkType(dataSource);
        return new InlineFeedbackSource(dataSource.data, workspace);
    }

    constructor(data, workspace) {
        super(data, workspace);
        this._cache = makeCache('averageEntries');
        Object.freeze(this);
    }

    get averageEntries() {
        const totalEntries = stat.sum(Object.values(this.data));
        const totalSubs = Object.keys(this.data).length;
        return totalEntries / totalSubs;
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

class WorkspaceSubmission {
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

    satisfiesGrade(filter) {
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
        // TODO: use the assignment's max grade instead of hardcoded
        // value 10.
        const { minGrade, maxGrade } = filter;

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

    satisfiesDate(filter) {
        // Same as with the grade, but we do not have a maximum value to check for.
        const { submittedAfter, submittedBefore } = filter;

        if (submittedAfter != null && this.createdAt.isBefore(submittedAfter)) {
            return false;
        }
        if (submittedBefore != null && !this.createdAt.isBefore(submittedBefore)) {
            return false;
        }
        return true;
    }
}

class WorkspaceSubmissionSet {
    static fromServerData(data) {
        const subs = mapObject(data, ss =>
            ss.map(WorkspaceSubmission.fromServerData),
        );
        return new WorkspaceSubmissionSet(subs);
    }

    constructor(subs) {
        this.submissions = mapObject(subs, Object.freeze);
        this._cache = makeCache(
            'allSubmissions',
            'averageGrade',
            'averageSubmissions',
            'submissionIds',
        );
        Object.freeze(this.subs);
    }

    get allSubmissions() {
        return this._cache.get('allSubmissions', () =>
            [].concat(...Object.values(this.submissions)),
        );
    }

    get submissionIds() {
        return this._cache.get('submissionIds', () =>
            new Set(this.allSubmissions.map(s => s.id)),
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
        const [start, end] = this.getDateRange(range);
        const binStep = moment.duration(binSize, binUnit).asMilliseconds();

        if (binStep === 0) {
            return {};
        }

        const getBin = d => {
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

    // eslint-disable-next-line
    getDateRange(range) {
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

        start = start.local().hours(0).minutes(0).seconds(0)
            .milliseconds(0);
        end = end.local().hours(23).minutes(59).seconds(59)
            .milliseconds(999);

        return [start, end];
    }

    get submissionCount() {
        return this.allSubmissions.length;
    }

    get studentCount() {
        return Object.keys(this.submissions).length;
    }

    get averageGrade() {
        return this._cache.get('averageGrade', () =>
            stat.mean(dropNull(this.allSubmissions.map(sub => sub.grade))),
        );
    }

    get averageSubmissions() {
        return this._cache.get('averageSubmissions', () =>
            this.submissionCount / this.studentCount,
        );
    }

    filter(filter) {
        let filtered = filter.onlyLatestSubs ?
            this.getLatestSubmissions() :
            this.submissions;

        filtered = mapObject(filtered, subs =>
            subs.filter(s => s.satisfiesGrade(filter) && s.satisfiesDate(filter)),
        );

        filtered = filterObject(filtered, subs => subs.length > 0);

        return new WorkspaceSubmissionSet(filtered);
    }

    getLatestSubmissions() {
        return mapObject(this.submissions, subs => {
            const [first, ...rest] = subs;
            const latest = rest.reduce(
                (a, b) => (a.createdAt.isAfter(b.createdAt) ? a : b),
                first,
            );
            return latest == null ? [] : [latest];
        });
    }
}

const WORKSPACE_FILTER_PROPS = new Set([
    'onlyLatestSubs',
    'minGrade',
    'maxGrade',
    'submittedAfter',
    'submittedBefore',
]);

export class WorkspaceFilter {
    constructor(props) {
        Object.keys(props).forEach(key => {
            if (!WORKSPACE_FILTER_PROPS.has(key)) {
                throw new Error(`Invalid filter: ${key}`);
            }
            this[key] = props[key];
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
        return new WorkspaceFilter({
            onlyLatestSubs: true,
            minGrade: null,
            maxGrade: null,
            submittedBefore: null,
            submittedAfter: null,
        });
    }

    update(key, value) {
        const x = new WorkspaceFilter(Object.assign({}, this, {
            // Convert empty string to null because <input>s return the empty
            // string if they're empty.
            [key]: value === '' ? null : value,
        }));
        return x;
    }

    split(props) {
        const {
            minGrade,
            maxGrade,
            submittedAfter,
            submittedBefore,
        } = this;

        const { latest, date } = props;
        const grade = parseFloat(props.grade);

        let result = [this];

        if (!Number.isNaN(grade)) {
            if (minGrade != null && minGrade >= grade) {
                throw new Error('Selected grade is less than or equal to the old "Min grade".');
            }
            if (maxGrade != null && maxGrade <= grade) {
                throw new Error('Selected grade is less than or equal to the old "Min grade".');
            }
            result = result.flatMap(f => [
                f.update('maxGrade', grade),
                f.update('minGrade', grade),
            ]);
        }

        if (date !== '') {
            if (submittedAfter != null && !submittedAfter.isBefore(date)) {
                throw new Error('Selected date is before the old "Submitted after".');
            }
            if (submittedBefore != null && !submittedBefore.isAfter(date)) {
                throw new Error('Selected date is after the old "Submitted before".');
            }
            result = result.flatMap(f => [
                f.update('submittedBefore', date),
                f.update('submittedAfter', date),
            ]);
        }

        if (latest) {
            result = result.flatMap(f => [
                f.update('onlyLatestSubs', false),
                f.update('onlyLatestSubs', true),
            ]);
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

            return parts.join(', ');
        });
    }
}

class WorkspaceFilterResult {
    constructor(workspace, filter) {
        this.workspace = workspace;
        this.filter = filter;
        this.submissions = workspace.submissions.filter(filter);

        const subIds = this.submissions.submissionIds;
        this.dataSources = Object.freeze(mapObject(
            workspace.dataSources,
            ds => ds.filter(subIds),
        ));

        Object.freeze(this);
    }

    getSource(sourceName) {
        return this.dataSources[sourceName];
    }
}

const WORKSPACE_SERVER_PROPS = Object.freeze([
    'id',
    'assignment_id',
]);

export class Workspace {
    static fromServerData(workspace, sources) {
        const props = WORKSPACE_SERVER_PROPS.reduce((acc, prop) => {
            acc[prop] = workspace[prop];
            return acc;
        }, {});

        props.submissions = WorkspaceSubmissionSet.fromServerData(
            workspace.student_submissions,
        );

        const self = new Workspace(props);

        const dataSources = workspace.data_sources.reduce((acc, src, i) => {
            acc[src] = createDataSource(sources[i], self);
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
        return Object.hasOwnProperty.call(this.dataSources, sourceName);
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
