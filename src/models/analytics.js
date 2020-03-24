/* SPDX-License-Identifier: AGPL-3.0-only */
import moment from 'moment';
import * as stat from 'simple-statistics';

import { store } from '@/store';
// eslint-ignore-next-line
import {
    getProps,
    mapObject,
    filterObject,
    zip,
} from '@/utils';
import { makeCache } from '@/utils/cache';

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

    filter(subIds, workspace) {
        const data = filterObject(this.data, (_, id) => subIds.has(parseInt(id, 10)));
        return new this.constructor(data, workspace);
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

const WORKSPACE_FILTER_PROPS = Object.freeze([
    'onlyLatestSubs',
    'minGrade',
    'maxGrade',
    'submittedAfter',
    'submittedBefore',
]);

export class WorkspaceFilter {
    constructor(props) {
        WORKSPACE_FILTER_PROPS.forEach(key => {
            if (!Object.hasOwnProperty.call(props, key)) {
                throw new Error('Filter prop not passed');
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

        Object.freeze(this);
    }

    apply(studentSubs) {
        let filtered = this.onlyLatestSubs ?
            WorkspaceFilter.getLatestSubs(studentSubs) :
            studentSubs;

        filtered = mapObject(filtered, subs =>
            subs.filter(s => this.satisfiesGrade(s) && this.satisfiesDate(s)),
        );
        filtered = filterObject(filtered, subs => subs.length > 0);

        return filtered;
    }

    satisfiesGrade(sub) {
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
        const { minGrade, maxGrade } = this;

        if (minGrade != null && sub.grade < minGrade) {
            return false;
        }
        if (maxGrade != null) {
            if (maxGrade === 10 && sub.grade === 10) {
                return true;
            }
            if (sub.grade >= maxGrade) {
                return false;
            }
        }
        return true;
    }

    satisfiesDate(sub) {
        // Same as with the grade, but we do not have a maximum value to check for.
        const { submittedAfter, submittedBefore } = this;

        if (submittedAfter != null && sub.createdAt.isBefore(submittedAfter)) {
            return false;
        }
        if (submittedBefore != null && !sub.createdAt.isBefore(submittedBefore)) {
            return false;
        }
        return true;
    }

    static getLatestSubs(studentSubs) {
        return mapObject(studentSubs, subs => {
            const [first, ...rest] = subs;
            const latest = rest.reduce(
                (a, b) => (a.createdAt.isAfter(b.createdAt) ? a : b),
                first,
            );
            return latest == null ? [] : [latest];
        });
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

        props.studentSubmissions = mapObject(workspace.student_submissions, subs =>
            subs.map(WorkspaceSubmission.fromServerData),
        );

        const self = new Workspace(props);

        const dataSources = workspace.data_sources.reduce((acc, src, i) => {
            acc[src] = createDataSource(sources[i], self);
            return acc;
        }, {});
        // eslint-disable-next-line
        self._setSources(dataSources);

        return self;
    }

    constructor(props, sources = null) {
        Object.assign(this, props);
        this.dataSources = {};
        this._cache = makeCache('allSubmissions', 'averageGrade', 'averageSubmissions');
        Object.freeze(this);

        if (sources != null) {
            this._setSources(sources);
        }
    }

    _setSources(dataSources) {
        Object.assign(this.dataSources, dataSources);
        Object.freeze(this.dataSources);
    }

    get assignment() {
        return store.getters['courses/assignments'][this.assignment_id];
    }

    get allSubmissions() {
        return this._cache.get('allSubmissions', () =>
            Object.values(this.studentSubmissions).reduce(
                (acc, subs) => acc.concat(subs),
                [],
            ),
        );
    }

    getSource(sourceName) {
        return this.dataSources[sourceName];
    }

    filter(filters) {
        if (filters.length === 0) {
            return this;
        }

        const filter = filters[0];

        const subs = filter.apply(this.studentSubmissions);
        const props = Object.assign({}, this, {
            studentSubmissions: subs,
        });
        const workspace = new Workspace(props);

        const allSubs = [].concat(...Object.values(subs));
        const subIds = new Set(Object.values(allSubs).map(sub => sub.id));
        const sources = mapObject(this.dataSources, ds => ds.filter(subIds, workspace));

        // eslint-disable-next-line
        workspace._setSources(sources);

        return workspace;
    }

    binSubmissionsBy(bins, f) {
        return this.allSubmissions.reduce((acc, sub) => {
            const idx = bins.findIndex((bin, i) => f(sub, bin, i));
            if (idx !== -1) {
                acc[idx].push(sub);
            }
            return acc;
        }, bins.map(() => []));
    }

    binSubmissionsByGrade(bins) {
        return this.binSubmissionsBy(bins, (sub, bin, i) => {
            const [low, high] = bin;
            const { grade } = sub;

            if (grade == null) {
                return false;
            } else if (i === bins.length - 1) {
                // Because we check the upper bound exclusively submissions
                // with the highest possible grade will not be put in the last
                // bin.
                return true;
            } else {
                return low <= grade && grade < high;
            }
        });
    }

    get submissionCount() {
        return this.allSubmissions.length;
    }

    get studentCount() {
        return Object.keys(this.studentSubmissions).length;
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

    gradeHistogram(bins) {
        return this.binSubmissionsByGrade(bins)
            .map(subs => subs.length);
    }
}
