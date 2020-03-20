/* SPDX-License-Identifier: AGPL-3.0-only */
import jStat from 'jstat';

import { store } from '@/store';
// eslint-ignore-next-line
import { getProps, mapObject, filterObject, zip } from '@/utils';
import { makeCache } from '@/utils/cache';

const WORKSPACE_SERVER_PROPS = [
    'id',
    'assignment_id',
    'student_submissions',
];

function dropNull(xs) {
    return xs.filter(x => x != null);
}

export class WorkspaceFilter {
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

    filter(keys) {
        const data = filterObject(this.data, (_, key) => keys.has(key));
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
                const rubricItem = this.rubricItems[item.item_id];
                item.points = item.multiplier * rubricItem.points;
                Object.freeze(item);
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
            this.mapItemsPerCat(items => jStat.mean(items.map(item => item.points)), true),
        );
    }

    get modePerCat() {
        return this._cache.get('modePerCat', () =>
            this.mapItemsPerCat(items => jStat.mode(items.map(item => item.points)), true),
        );
    }

    get medianPerCat() {
        return this._cache.get('medianPerCat', () =>
            this.mapItemsPerCat(items => jStat.median(items.map(item => item.points)), true),
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
                jStat.sum(Object.values(scorePerCat)),
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
                return jStat.corrcoeff(...zip(...filtered));
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
                return jStat.corrcoeff(...zip(...filtered));
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
        const totalEntries = jStat.sum(Object.values(this.data));
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

export class Workspace {
    static fromServerData(workspace, sources) {
        const props = WORKSPACE_SERVER_PROPS.reduce((acc, prop) => {
            acc[prop] = workspace[prop];
            return acc;
        }, {});
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
            Object.values(this.student_submissions).reduce(
                (acc, subs) => acc.concat(subs),
                [],
            ),
        );
    }

    getSource(sourceName) {
        return this.dataSources[sourceName];
    }

    filter() {
        // TODO: implement filter
        const newWs = Object.assign({}, this, {
            student_submissions: this.student_submissions,
        });
        return new Workspace(newWs, this.dataSources);
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

    get averageGrade() {
        return this._cache.get('averageGrade', () =>
            jStat.mean(dropNull(this.allSubmissions.map(sub => sub.grade))),
        );
    }

    get averageSubmissions() {
        return this._cache.get('averageSubmissions', () => {
            const totalSubs = this.allSubmissions.length;
            const totalStudents = Object.keys(this.student_submissions).length;
            return totalSubs / totalStudents;
        });
    }

    gradeHistogram(bins) {
        return this.binSubmissionsByGrade(bins)
            .map(subs => subs.length);
    }
}
