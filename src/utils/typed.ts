function fromEntries<T>(vals: [string, T][]): Record<string, T> {
    return (Object as any).fromEntries(vals);
}

export function hasAttr<T>(obj: T, key: PropertyKey): key is keyof T {
    return Object.hasOwnProperty.call(obj, key);
}

export function mapObject<T, V>(
    obj: { [key: string]: T },
    fun: (v: T, k: string) => V,
): Record<string, V> {
    return fromEntries(Object.entries(obj).map(([key, val]) => [key, fun(val, key)]));
}

export function flatMap<T, TT>(arr: ReadonlyArray<T>, mapper: (val: T) => TT[]): TT[] {
    return (arr as any).flatMap(mapper);
}

export function zip<T, Y>(a: T[], b: Y[]): [T, Y][];
export function zip(...lists: any[][]): any {
    if (lists.length === 0) {
        return [];
    }

    const acc = [];
    const end = Math.min(...lists.map(l => l.length));
    let i = 0;
    const getter = (l: any[]) => l[i];

    for (; i < end; i++) {
        acc.push(lists.map(getter));
    }
    return acc;
}

export function unzip2<T, Y>(arr: [T, Y][]): [T[], Y[]] {
    const base: [T[], Y[]] = [[], []];

    return arr.reduce((acc, item: [T, Y]) => {
        acc[0].push(item[0]);
        acc[1].push(item[1]);
        return acc;
    }, base);
}

export function flat<T>(arr: T[][]): T[] {
    return (arr as any).flat(1);
}
