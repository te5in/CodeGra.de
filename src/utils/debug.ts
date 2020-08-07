export function trace<X>(x: X, transform: (x: X) => any = y => y): X {
    console.log(transform(x), new Error().stack);
    return x;
}
