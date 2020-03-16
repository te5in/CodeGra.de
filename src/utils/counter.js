export class Counter {
    constructor(items) {
        this._counts = items.reduce((acc, item) => {
            if (!acc.has(item)) {
                acc.set(item, 0);
            }
            acc.set(item, acc.get(item) + 1);
            return acc;
        }, new Map());

        Object.freeze(this._counts);
        Object.freeze(this);
    }

    getCount(item) {
        const amount = this._counts.get(item);
        if (amount === undefined) {
            return 0;
        }
        return amount;
    }
}
