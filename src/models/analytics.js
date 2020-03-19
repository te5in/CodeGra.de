import jStat from 'jstat';

import { UNSET_SENTINEL } from '@/constants';
import { mapObject } from '@/utils';

function zip(...lists) {
    if (lists.length === 0) {
        return [];
    }

    const acc = [];
    const end = jStat.min(lists.map(l => l.length));
    for (let i = 0; i < end; i++) {
        // eslint-disable-next-line no-loop-func
        acc.push(lists.map(l => l[i]));
    }
    return acc;
}

function dropNull(xs) {
    return xs.filter(x => x != null);
}

export class RubricResults {
    constructor(rubric, results) {
        this.rubric = rubric;
        this.rowIds = rubric.rows.map(row => row.id);
        this.results = results;

        this._cache = Object.seal({
            totalScorePerStudent: UNSET_SENTINEL,
            nTimesFilledPerCat: UNSET_SENTINEL,
            scoresPerStudent: UNSET_SENTINEL,
            ritItemsPerCat: UNSET_SENTINEL,
            rirItemsPerCat: UNSET_SENTINEL,
            scoresPerCat: UNSET_SENTINEL,
            meanPerCat: UNSET_SENTINEL,
            ritPerCat: UNSET_SENTINEL,
            rirPerCat: UNSET_SENTINEL,
        });
    }

    get scoresPerStudent() {
        if (this._cache.scoresPerStudent === UNSET_SENTINEL) {
            this._cache.scoresPerStudent = this.results.map(result =>
                mapObject(result.selected, item => item.achieved_points),
            );
        }
        return this._cache.scoresPerStudent;
    }

    get totalScorePerStudent() {
        if (this._cache.totalScorePerStudent === UNSET_SENTINEL) {
            this._cache.totalScorePerStudent = this.scoresPerStudent.map(result =>
                jStat.sum(dropNull(Object.values(result))),
            );
        }
        return this._cache.totalScorePerStudent;
    }

    get scoresPerCat() {
        if (this._cache.scoresPerCat === UNSET_SENTINEL) {
            this._cache.scoresPerCat = this.scoresPerStudent.reduce(
                (acc, result) => {
                    this.rowIds.forEach(rowId => acc[rowId].push(result[rowId]));
                    return acc;
                },
                Object.fromEntries(this.rowIds.map(id => [id, []])),
            );
        }
        return this._cache.scoresPerCat;
    }

    get meanPerCat() {
        if (this._cache.meanPerCat === UNSET_SENTINEL) {
            this._cache.meanPerCat = mapObject(this.scoresPerCat, scores => {
                const mu = jStat.mean(dropNull(scores));
                return Number.isNaN(mu) ? 0 : mu;
            });
        }
        return this._cache.meanPerCat;
    }

    get ritItemsPerCat() {
        if (this._cache.ritItemsPerCat === UNSET_SENTINEL) {
            this._cache.ritItemsPerCat = this.rowIds.reduce((acc, rowId) => {
                acc[rowId] = zip(this.scoresPerCat[rowId], this.totalScorePerStudent).filter(
                    ([s]) => s != null,
                );
                return acc;
            }, {});
        }
        return this._cache.ritItemsPerCat;
    }

    get ritPerCat() {
        if (this._cache.ritPerCat === UNSET_SENTINEL) {
            this._cache.ritPerCat = mapObject(this.ritItemsPerCat, catScores => {
                const [scores, totalScores] = zip(...catScores);
                if (scores && totalScores) {
                    const rit = jStat.corrcoeff(scores, totalScores);
                    return Number.isNaN(rit) ? 0 : rit;
                } else {
                    return null;
                }
            });
        }
        return this._cache.ritPerCat;
    }

    get rirItemsPerCat() {
        if (this._cache.rirItemsPerCat === UNSET_SENTINEL) {
            this._cache.rirItemsPerCat = mapObject(this.ritItemsPerCat, catScores =>
                catScores.map(([itemScore, totalScore]) => [itemScore, totalScore - itemScore]),
            );
        }
        return this._cache.rirItemsPerCat;
    }

    get rirPerCat() {
        if (this._cache.rirPerCat === UNSET_SENTINEL) {
            this._cache.rirPerCat = mapObject(this.rirItemsPerCat, catScores => {
                const [scores, totalScores] = zip(...catScores);
                if (scores && totalScores) {
                    const rir = jStat.corrcoeff(scores, totalScores);
                    return Number.isNaN(rir) ? 0 : rir;
                } else {
                    return null;
                }
            });
        }
        return this._cache.rirPerCat;
    }

    get nTimesFilledPerCat() {
        if (this._cache.nTimesFilledPerCat === UNSET_SENTINEL) {
            this._cache.nTimesFilledPerCat = mapObject(
                this.scoresPerCat,
                scores => dropNull(scores).length,
            );
        }
        return this._cache.nTimesFilledPerCat;
    }
}
