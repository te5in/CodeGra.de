export class Rubric {
    constructor(rows, assignment) {
        this.rows = (rows || []).map(row => {
            row.items.sort((x, y) => x.points - y.points);
            row.maxPoints = Math.max(...row.items.map(item => item.points));
            return row;
        });
        this.items = (rows || []).reduce(
            (acc, row) =>
                Object.assign(
                    acc,
                    row.items.reduce((items, item) => {
                        items[item.id] = item;
                        return items;
                    }),
                ),
            {},
        );
        this.assignment = assignment;
        if (assignment.fixed_max_rubric_points != null) {
            this.maxPoints = this.assignment.fixed_max_rubric_points;
        } else {
            this.maxPoints = this.rows.reduce((acc, row) => acc + row.maxPoints, 0);
        }
    }
}

export class RubricResult {
    constructor(result) {
        const { selected } = result;
        this.selected = selected;
        this.selectedById = RubricResult.getSelectedById(selected);
        this.points =
            selected.length === 0 ? null : selected.reduce((acc, { points }) => acc + points, 0);
    }

    copy() {
        return new RubricResult(this);
    }

    // We need to use `this` according to eslint, but this method might copy
    // more data from this in the future, but at the moment it doesn't.
    // eslint-disable-next-line
    setSelected(selected) {
        return new RubricResult({
            selected,
        });
    }

    static getSelectedById(selected) {
        return selected.reduce((acc, item) => {
            acc[item.id] = item;
            return acc;
        }, {});
    }

    isSelected(item) {
        return item.id in this.selectedById;
    }

    toggleItem(row, item) {
        if (this.isSelected(item)) {
            return this.unselectItem(row, item);
        }
        return this.selectItem(row, item);
    }

    selectItem(row, item) {
        const toRemove = row.items.find(this.isSelected.bind(this));
        const newSelected = [
            ...this.selected.filter(({ id }) => (toRemove ? id !== toRemove.id : true)),
            item,
        ];
        return this.setSelected(newSelected);
    }

    unselectItem(row, item) {
        const newSelected = this.selected.filter(({ id }) => id !== item.id);
        if (newSelected.length === this.selected.length) {
            throw new ReferenceError('Item is not selected.');
        }
        return this.setSelected(newSelected);
    }
}
