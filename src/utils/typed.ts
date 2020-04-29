export type AllOrNone<T> = T | { [K in keyof T]?: never };

function fromEntries<T>(vals: [string, T][]): Record<string, T> {
    return (Object as any).fromEntries(vals);
}

export function hasAttr<T>(obj: T, key: PropertyKey): key is keyof T {
    return Object.hasOwnProperty.call(obj, key);
}

export function filterObject<T>(
    obj: { [key: string]: T },
    f: (v: T, k: string) => boolean,
): Record<string, T> {
    return fromEntries(Object.entries(obj).filter(([key, val]) => f(val, key)));
}

export function mapObject<T, V>(
    obj: { [key: string]: T },
    fun: (v: T, k: string) => V,
): Record<string, V> {
    return fromEntries(Object.entries(obj).map(([key, val]) => [key, fun(val, key)]));
}

// Map over an array, allowing to provide a custom map function for the first
// or last element.
export function mapCustom<T, V>(
    arr: Array<T>,
    fun: (v: T, i: number) => V,
    first: (v: T, i: number) => V = fun,
    last: (v: T, i: number) => V = fun,
): Array<V> {
    const max = arr.length - 1;
    return arr.map((v, i) => {
        if (i === 0) {
            return first(v, i);
        } else if (i === max) {
            return last(v, i);
        } else {
            return fun(v, i);
        }
    });
}

export function flatMap1<T, TT>(
    arr: ReadonlyArray<T>,
    mapper: (val: T, index: number) => TT[],
): TT[] {
    return arr.reduce((acc: TT[], elem: T, index: number) => acc.concat(mapper(elem, index)), []);
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

export function flat1<T>(arr: T[][]): T[] {
    return arr.reduce((acc, elem) => acc.concat(elem), []);
}

export function unique<T, V>(arr: ReadonlyArray<T>, getKey: (item: T) => V): T[] {
    const seen = new Set();
    return arr.reduce((acc: T[], item: T) => {
        const key = getKey(item);
        if (!seen.has(key)) {
            seen.add(key);
            acc.push(item);
        }
        return acc;
    }, []);
}

export class AssertionError extends Error {
    static assert(condition: false, msg?: string): never;

    static assert(condition: boolean, msg?: string): asserts condition {
        if (!condition) {
            throw new AssertionError(msg);
        }
    }
}

export function buildUrl(
    parts: ReadonlyArray<string | number> | string,
    args: {
        query?: Record<string, string>;
        hash?: string;
        addTrailingSlash?: boolean;
    } & AllOrNone<{
        host: string;
        protocol: string;
    }> = {},
): string {
    let mainPart;
    let initialSlash = '';
    if (typeof parts === 'string') {
        mainPart = parts;
    } else {
        initialSlash = '/';
        mainPart = parts.map(part => encodeURIComponent(part)).join('/');
    }
    if (args.addTrailingSlash) {
        mainPart = `${mainPart}/`;
    }

    let prefix = '';
    if (args.protocol != null) {
        initialSlash = '/';
        prefix = `${args.protocol.toString()}//${args.host.toString()}`;
    }

    let query = '';
    if (args.query) {
        const params = Object.entries(args.query)
            .reduce((acc, [key, value]) => {
                acc.append(key, value);
                return acc;
            }, new URLSearchParams())
            .toString();
        query = `?${params}`;
    }

    let hash = '';
    if (args.hash) {
        hash = `#${encodeURIComponent(args.hash)}`;
    }

    return `${prefix}${initialSlash}${mainPart}${query}${hash}`;
}

export function capitalize(str: string): string {
    if (str.length === 0) return str;
    return str[0].toUpperCase() + str.substr(1);
}

export function titleCase(str: string): string {
    return str
        .split(' ')
        .map(capitalize)
        .join(' ');
}

export const getUniqueId = (() => {
    let id = 0;
    return () => id++;
})();

export function waitAtLeast<T>(time: number, promise: Promise<T>): Promise<T>;

export function waitAtLeast<T, Y>(
    time: number,
    promise: Promise<T>,
    ...promises: Promise<Y>[]
): Promise<[T, ...Y[]]>;

export function waitAtLeast<T>(time: number, ...promises: Promise<T>[]): Promise<T | T[]> {
    const timeout: Promise<undefined> = new Promise(resolve => setTimeout(resolve, time));

    return Promise.all([timeout, Promise.all(promises)]).then(([_, vals]) => {
        if (promises.length === 1) {
            return vals[0];
        } else {
            return vals;
        }
    });
}

export function getProps<TObj extends object, TKey extends keyof TObj, TDefault>(
    object: TObj,
    defaultValue: TDefault,
    prop: TKey,
): Exclude<TObj[TKey], undefined> | TDefault;

export function getProps<TObj extends object, TKey extends keyof TObj, TDefault>(
    object: TObj,
    defaultValue: TDefault,
    prop: Omit<string, TKey>,
): TDefault;

export function getProps<
    TObj extends object,
    TKey1 extends keyof TObj,
    TKey2 extends keyof TObj[TKey1],
    TDefault
>(
    object: TObj,
    defaultValue: TDefault,
    prop1: TKey1,
    prop2: TKey2,
): Exclude<TObj[TKey1][TKey2], undefined> | TDefault;

export function getProps<
    TObj extends object,
    TKey1 extends keyof TObj,
    TKey2 extends keyof TObj[TKey1],
    TKey3 extends keyof TObj[TKey1][TKey2],
    TDefault
>(
    object: TObj,
    defaultValue: TDefault,
    prop1: TKey1,
    prop2: TKey2,
    prop3: TKey3,
): Exclude<TObj[TKey1][TKey2][TKey3], undefined> | TDefault;

export function getProps<
    TObj extends object,
    TKey1 extends keyof TObj,
    TKey2 extends keyof TObj[TKey1],
    TKey3 extends keyof TObj[TKey1][TKey2],
    TDefault
>(
    object: TObj,
    defaultValue: TDefault,
    prop1: Omit<string, TKey1>,
    ...otherProps: string[]
): TDefault;

export function getProps<T, Y, K extends string>(
    object: Record<K, T> | null | undefined,
    defaultValue: Y,
    ...props: K[]
): T | Y {
    let res: Record<string, Object> | undefined | null = object;
    for (let i = 0; res != null && i < props.length; ++i) {
        res = res[props[i]];
    }
    if (res == null) {
        return defaultValue;
    }
    return res as any;
}

export function ensureArray<T>(obj: T | ReadonlyArray<T>): T[] {
    return Array.isArray(obj) ? obj : [obj];
}

// https://stackoverflow.com/questions/13405129/javascript-create-and-save-file
export function downloadFile(data: string, filename: string, contentType: string) {
    const file = new Blob([data], { type: contentType });
    if (window.navigator.msSaveOrOpenBlob) {
        // IE10+
        window.navigator.msSaveOrOpenBlob(file, filename);
    } else {
        const url = URL.createObjectURL(file);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        setTimeout(() => {
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }, 0);
    }
}
