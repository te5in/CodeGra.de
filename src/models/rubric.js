import Vue from 'vue';

export class Rubric {
    constructor(rows) {
        this.rows = rows.map(row => {
            row.items.sort((x, y) => x.points - y.points);
            row.maxPoints = Math.max(...row.items.map(item => item.points));
            return row;
        });
        this.items = rows.reduce(
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
        this.maxPoints = rows.reduce((acc, row) => acc + row.maxPoints, 0);
    }
}

export class RubricResult {
    constructor(result) {
        this.setSelected(result.selected);
    }

    setSelected(selected) {
        this.selected = selected;
        this.points =
            selected.length === 0 ? null : selected.reduce((acc, { points }) => acc + points, 0);
    }

    selectItem(row, item) {
        const selectedIds = this.selected.reduce((acc, s, i) => {
            acc[s.id] = i;
            return acc;
        }, {});

        row.items.forEach(({ id, points }) => {
            if (selectedIds[id] != null) {
                this.points -= points;
                this.selected.splice(selectedIds[id], 1);
            }
        });

        Vue.set(this, 'points', this.points + item.points);
        Vue.set(this, 'selected', this.selected.concat([item]));
    }

    unselectItem(row, item) {
        const i = this.selected.findIndex(x => x.id === item.id);

        if (i === -1) {
            throw new ReferenceError('Item is not selected.');
        }

        Vue.delete(this.selected, i);

        if (this.selected.length) {
            Vue.set(this, 'points', this.points - item.points);
        } else {
            Vue.set(this, 'points', null);
        }
    }
}
