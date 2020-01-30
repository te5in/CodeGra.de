import { UNSET_SENTINEL } from '@/constants';
import { store } from '@/store';
import { formatGrade, getProps, getUniqueId, toMaxNDecimals, setXor } from '@/utils';
import { RubricResultValidationError, RubricRowValidationError } from './errors';

export class RubricItem {
    static fromServerData(data) {
        return new RubricItem({
            id: data.id,
            points: data.points,
            header: data.header,
            description: data.description,
        });
    }

    static createEmpty() {
        return new RubricItem({
            id: undefined,
            points: '',
            header: '',
            description: '',
            trackingId: getUniqueId(),
        });
    }

    constructor(item) {
        Object.assign(this, item);
        Object.freeze(this);
    }

    update(props = {}) {
        return new RubricItem(Object.assign({}, this, props));
    }

    get nonEmptyHeader() {
        return this.header || '[No name]';
    }
}

const RubricRowsTypes = {};

export class RubricRow {
    static fromServerData(data) {
        const cls = RubricRowsTypes[data.type];
        if (cls == null) {
            throw new ReferenceError(`Could not find specified type: ${data.type}`);
        }
        return cls.fromServerData(data);
    }

    static createEmpty() {
        return new RubricRow({
            type: '',
            header: '',
            description: '',
            locked: false,
            items: [],
        });
    }

    constructor(row) {
        if (row.type && !(this instanceof RubricRowsTypes[row.type])) {
            throw new Error('You cannot make a base row with a non empty type.');
        }
        Object.assign(this, row);
        Object.freeze(this.items);

        this._cache = Object.seal({
            maxPoints: UNSET_SENTINEL,
        });

        Object.freeze(this);
    }

    get maxPoints() {
        if (this._cache.maxPoints === UNSET_SENTINEL) {
            let maxPoints = Math.max(
                ...this.items.map(item => item.points).filter(pts => pts != null),
            );

            if (maxPoints === -Infinity) {
                maxPoints = 0;
            }

            this._cache.maxPoints = maxPoints;
        }

        return this._cache.maxPoints;
    }

    update(props = {}) {
        return new this.constructor(Object.assign({}, this, props));
    }

    updateItem(idx, prop, value) {
        const items = this.items.slice();
        if (idx < 0 || idx >= items.length) {
            throw new ReferenceError('Invalid index');
        }
        if (prop === 'points') {
            const pts = parseFloat(value);
            items[idx] = items[idx].update({
                points: Number.isNaN(pts) ? null : pts,
            });
        } else {
            items[idx] = items[idx].update({ [prop]: value });
        }
        return this.update({ items });
    }

    setType(type) {
        if (this.type != null && this.type !== '') {
            throw new Error(`Row type was already set and was ${this.type}`);
        }

        const cls = RubricRowsTypes[type];
        if (cls == null) {
            throw new TypeError(`Invalid row type: ${type}`);
        }
        return cls.createEmpty();
    }

    createItem() {
        return this.update({
            items: this.items.concat(RubricItem.createEmpty()),
        });
    }

    deleteItem(idx) {
        if (idx < 0 || idx >= this.items.length) {
            throw new ReferenceError('Invalid index');
        }

        return this.update({
            items: this.items.slice(0, idx).concat(this.items.slice(idx + 1)),
        });
    }

    lockMessage(autoTest, autoTestResult, rubricResult) {
        switch (this.locked) {
            case 'auto_test':
                return this._autoTestLockMessage(autoTest, autoTestResult, rubricResult);
            default:
                return '';
        }
    }

    _autoTestLockMessage(autoTest, autoTestResult, rubricResult) {
        const selectedRubricItem = getProps(rubricResult, null, 'selected', this.id);
        const autoTestPercentage = getProps(
            autoTestResult,
            null,
            'rubricResults',
            this.id,
            'percentage',
        );

        if (selectedRubricItem == null || autoTestPercentage == null) {
            let msg = 'This is an AutoTest category.';
            if (autoTestResult != null) {
                const extra = [];
                if (!autoTestResult.finished) {
                    extra.push('the test has finished running');
                }
                if (!autoTestResult.isFinal) {
                    extra.push(
                        'all hidden steps have been run, which will happen after the deadline',
                    );
                }
                if (extra.length === 0) {
                    extra.push('you have the permission to see the final grade');
                }
                msg += ` It will be filled in once ${extra.join(' and ')}.`;
            }
            return msg;
        } else {
            return `You scored ${autoTestPercentage.toFixed(
                0,
            )}% in the corresponding AutoTest category, which scores you ${toMaxNDecimals(
                selectedRubricItem.points * selectedRubricItem.multiplier,
                2,
            )} points in this rubric category. `;
        }
    }

    get nonEmptyHeader() {
        return this.header || '[No name]';
    }

    validate(prevErrors = null) {
        let errors = prevErrors;
        if (errors == null) {
            errors = new RubricRowValidationError();
        } else if (!(errors instanceof RubricRowValidationError)) {
            throw new Error('prevErrors should be an instance of RubricRowValidationError');
        }

        if (this.header.length === 0) {
            errors.unnamed = true;
        }

        if (this.items.length === 0) {
            errors.categories.push(this.nonEmptyHeader);
        }

        for (let j = 0; j < this.items.length; j += 1) {
            const item = this.items[j];

            if (item.header.length === 0) {
                errors.itemHeader.push(this.nonEmptyHeader);
            }

            if (Number.isNaN(parseFloat(item.points))) {
                errors.itemPoints.push(`'${this.nonEmptyHeader} - ${item.nonEmptyHeader}'`);
            }
        }

        return errors;
    }
}

export class NormalRubricRow extends RubricRow {
    static fromServerData(data) {
        if (data.type !== 'normal') {
            throw new TypeError('Row is not normal');
        }

        return new NormalRubricRow({
            id: data.id,
            type: data.type,
            header: data.header,
            description: data.description,
            locked: data.locked,
            items: data.items.map(item => RubricItem.fromServerData(item)),
        });
    }

    static createEmpty() {
        return new NormalRubricRow({
            type: 'normal',
            header: '',
            description: '',
            locked: false,
            items: [],
        });
    }

    _autoTestLockMessage(autoTest, autoTestResult, rubricResult) {
        const gradeCalculation = getProps(autoTest, null, 'grade_calculation');
        let msg = super._autoTestLockMessage(autoTest, autoTestResult, rubricResult);
        if (msg) {
            msg += ' ';
        }

        if (gradeCalculation != null) {
            msg += `You need to reach the ${
                gradeCalculation === 'full' ? 'upper' : 'lower'
            } bound of a rubric item to achieve its score.`;
        } else {
            msg += 'No grade calculation method has been set yet.';
        }

        return msg;
    }
}
RubricRowsTypes.normal = NormalRubricRow;

export class ContinuousRubricRow extends RubricRow {
    static fromServerData(data) {
        if (data.type !== 'continuous') {
            throw new TypeError('Row is not continuous');
        }

        return new ContinuousRubricRow({
            id: data.id,
            type: data.type,
            header: data.header,
            description: data.description,
            locked: data.locked,
            items: data.items.map(item => RubricItem.fromServerData(item)),
        });
    }

    static createEmpty() {
        return new ContinuousRubricRow({
            type: 'continuous',
            header: '',
            description: '',
            locked: false,
            items: [RubricItem.createEmpty().update({ header: 'Continuous' })],
        });
    }

    validate(prevErrors = null) {
        const errors = super.validate(prevErrors);

        if (this.items[0].points <= 0) {
            errors.continuous.push(this.nonEmptyHeader);
        }

        return errors;
    }
}

RubricRowsTypes.continuous = ContinuousRubricRow;

export class Rubric {
    static fromServerData(data) {
        const rows = (data || []).map(row => {
            row.items.sort((x, y) => x.points - y.points);
            return RubricRow.fromServerData(row);
        });

        return new Rubric(rows);
    }

    constructor(rows) {
        this.rows = Object.freeze(rows);
        this._cache = Object.seal({
            maxPoints: UNSET_SENTINEL,
            rowsById: UNSET_SENTINEL,
        });

        Object.freeze(this);
    }

    get maxPoints() {
        if (this._cache.maxPoints === UNSET_SENTINEL) {
            this._cache.maxPoints = this.rows.reduce((acc, row) => acc + row.maxPoints, 0);
        }

        return this._cache.maxPoints;
    }

    get rowsById() {
        if (this._cache.rowsById === UNSET_SENTINEL) {
            this._cache.rowsById = this.rows.reduce((acc, row) => {
                acc[row.id] = row;
                return acc;
            }, {});
        }

        return this._cache.rowsById;
    }

    getItemIds() {
        return this.rows.reduce((acc, row) => {
            row.items.forEach(item => {
                if (item.id != null) {
                    acc[item.id] = `${row.nonEmptyHeader} - ${item.nonEmptyHeader}`;
                }
            });
            return acc;
        }, {});
    }

    createRow() {
        const rows = this.rows.concat(RubricRow.createEmpty());
        return new Rubric(rows);
    }

    deleteRow(idx) {
        if (idx < 0 || idx >= this.rows.length) {
            throw new ReferenceError('Invalid index');
        }

        const rows = this.rows.slice(0, idx).concat(this.rows.slice(idx + 1));
        return new Rubric(rows);
    }

    updateRow(idx, rowData) {
        if (!(rowData instanceof RubricRow)) {
            throw new TypeError('Rubric rows must be of type RubricRow');
        }

        const rows = this.rows.slice();
        rows[idx] = rowData;
        return new Rubric(rows);
    }
}

export class RubricResult {
    static fromServerData(submissionId, data) {
        const rowOfItem = data.rubrics.reduce((acc, row) => {
            row.items.forEach(item => {
                acc[item.id] = row.id;
            });
            return acc;
        }, {});

        const selected = data.selected.reduce((acc, item) => {
            const rowId = rowOfItem[item.id];
            acc[rowId] = item;
            return acc;
        }, {});

        return new RubricResult(submissionId, selected);
    }

    constructor(submissionId, selected) {
        this.submissionId = submissionId;
        this.selected = Object.freeze(selected);
        this._cache = Object.seal({ points: UNSET_SENTINEL });

        Object.freeze(this);
    }

    get points() {
        if (this._cache.points === UNSET_SENTINEL) {
            if (Object.values(this.selected).length === 0) {
                this._cache.points = null;
            } else {
                this._cache.points = Object.values(this.selected).reduce((acc, item) => {
                    if (typeof item.multiplier !== 'number') {
                        return acc;
                    }
                    const multiplier = Math.max(0, Math.min(item.multiplier, 1));
                    return acc + item.points * multiplier;
                }, 0);
            }
        }

        return this._cache.points;
    }

    get nSelected() {
        return Object.keys(this.selected).length;
    }

    get submission() {
        return store.getters['submissions/getSingleSubmission'](this.submissionId);
    }

    get rubric() {
        const id = getProps(this.submission, null, 'assignmentId');
        return id == null ? null : store.getters['rubrics/rubrics'][id];
    }

    getGrade(maxPoints) {
        if (this.nSelected === 0) {
            return null;
        } else {
            const grade = 10 * this.points / maxPoints;
            return formatGrade(Math.max(0, Math.min(grade, 10)));
        }
    }

    diffSelected(other) {
        const ownIds = new Set(Object.values(this.selected).map(x => x.id));
        const otherIds = new Set(Object.values(other.selected).map(x => x.id));

        return setXor(ownIds, otherIds);
    }

    toggleItem(rowId, item) {
        const selected = Object.assign({}, this.selected);
        const selectedItem = selected[rowId];

        if (selectedItem && selectedItem.id === item.id) {
            delete selected[rowId];
        } else {
            selected[rowId] = Object.assign({}, item, {
                multiplier: 1,
            });
        }

        return new RubricResult(this.submissionId, selected);
    }

    setMultiplier(rowId, item, multiplier) {
        const selected = Object.assign({}, this.selected);
        const selectedItem = selected[rowId];

        if (selectedItem && selectedItem.id !== item.id) {
            throw new Error(
                `Item id should not change! Expected ${selectedItem.id} but got ${item.id}.`,
            );
        } else if (multiplier == null) {
            delete selected[rowId];
        } else {
            selected[rowId] = Object.assign({}, item, {
                multiplier: Number(multiplier),
            });
        }

        return new RubricResult(this.submissionId, selected);
    }

    validate() {
        if (this.rubric == null) {
            throw new ReferenceError('Rubric not found.');
        }

        const errors = new RubricResultValidationError();
        const rows = this.rubric.rowsById;

        Object.entries(this.selected).forEach(([rowId, item]) => {
            const row = rows[rowId];
            if (item.multiplier != null && (item.multiplier < 0 || item.multiplier > 1)) {
                errors.multipliers.push(row.nonEmptyHeader);
            }
        });

        return errors;
    }

    // eslint-disable-next-line class-methods-use-this
    clearSelected() {
        return new RubricResult(this.submissionId, {});
    }
}
