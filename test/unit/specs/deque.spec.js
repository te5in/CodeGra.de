import Deque from '@/utils/deque';

// These tests are pretty bare bones, but mostly our implementation is simply a
// well tested implementation of npm. So we only need to test our additions.

describe('setAt function of deque', () => {
    let deq;
    const origArr = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9];

    beforeEach(() => {
        deq = new Deque(origArr);
    });

    it('should be possible to set a value', () => {
        expect(deq.setAt(2, 100)).toBe(2);
        expect(deq.toArray()).toEqual(origArr.map(x => x === 2 ? 100 : x));
    });

    it('should be possible to use a negative index', () => {
        expect(deq.setAt(-1, 100)).toBe(9);
        expect(deq.toArray()).toEqual(origArr.map(x => x === 9 ? 100 : x));
    });

    it('should return undefined for out of bounds', () => {
        expect(deq.setAt(15, 150)).toBe(undefined);
        expect(deq.toArray()).toEqual(origArr);
    });
});
