export function defaultdict(defaultType) {
    return new Proxy(
        {},
        {
            get(target, key, receiver) {
                if (!Reflect.has(target, key)) {
                    Reflect.set(target, key, defaultType(key), receiver);
                }
                return Reflect.get(target, key, receiver);
            },

            set(target, key, value, receiver) {
                Reflect.set(target, key, value, receiver);
            },
        },
    );
}
