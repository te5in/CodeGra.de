import axios from 'axios';
import { store } from '@/store';
import * as types from '@/store/mutation-types';

const mockFormatGrade = jest.fn();
const mockAxiosGet = jest.fn();
axios.get = mockAxiosGet;

function fillBuf(buf) {
    for (let i = 0; i < buf.length; ++i) {
        buf[i] = Math.round(Math.random() * 1000);
    }
    return buf;
}

describe('loading code', () => {
    let buf1;
    let buf2;

    beforeEach(() => {
        buf1 = fillBuf(new ArrayBuffer(100000));
        buf2 = fillBuf(new ArrayBuffer(500000));
        mockAxiosGet.mockReset();
        store.commit(`code/${types.CLEAR_CODE_CACHE}`, null, { root: true });
    });

    it('should work for new code', async () => {
        mockAxiosGet.mockReturnValueOnce(Promise.resolve({ data: buf1 }));
        const code = await store.dispatch('code/loadCode', 50);
        expect(code).toEqual(buf1);
        expect(mockAxiosGet).toBeCalledTimes(1);
        expect(mockAxiosGet).toBeCalledWith(`/api/v1/code/50`, { responseType: 'arraybuffer' });
    });

    it('loading twice should only use api once', async () => {
        mockAxiosGet.mockReturnValueOnce(Promise.resolve({ data: buf1 }));
        const code = await store.dispatch('code/loadCode', 50);
        expect(code).toEqual(buf1);
        const code2 = await store.dispatch('code/loadCode', 50);
        expect(code).toEqual(buf1);
        expect(mockAxiosGet).toBeCalledTimes(1);
        // It should decompress again, so it should be a new arraybuffer.
        expect(code2).not.toBe(code);
    });

    it('should clear old items when cache becomes too large', async () => {
        mockAxiosGet.mockReturnValue(Promise.resolve({ data: buf2 }));
        const amount = Math.round(2 ** 9.5);
        for (let i = 0; i < amount; ++i) {
            await store.dispatch('code/loadCode', i);
            await store.dispatch('code/loadCode', 0);
        }
        expect(mockAxiosGet).toBeCalledTimes(amount);

        // This was the first item stored, so that one should be removed.
        mockAxiosGet.mockClear();
        await store.dispatch('code/loadCode', 1);
        expect(mockAxiosGet).toBeCalledTimes(1);

        // This is one of the last items stored, so that should still be in the
        // cache.
        mockAxiosGet.mockClear();
        await store.dispatch('code/loadCode', amount - 1);
        expect(mockAxiosGet).toBeCalledTimes(0);

        // As we accessed code with id 0 all the time it should still be in the
        // cache.
        mockAxiosGet.mockClear();
        await store.dispatch('code/loadCode', 0);
        expect(mockAxiosGet).toBeCalledTimes(0);
    });

    it('should not cache very large objects', async () => {
        mockAxiosGet.mockReturnValueOnce(Promise.resolve({ data: buf1 }));
        await store.dispatch('code/loadCode', -1);
        mockAxiosGet.mockReturnValue(Promise.resolve({ data: fillBuf(new ArrayBuffer(2 ** 30)) }));
        await store.dispatch('code/loadCode', 1);

        console.log(store.state.code.cacheMap);
        console.log(store.state.code.cacheMap[-1]);
        console.log(store.state.code.cacheMap[1]);

        expect(mockAxiosGet).toBeCalledTimes(2);

        mockAxiosGet.mockClear();

        expect(store.getters['code/getCachedCode']('/api/v1/code/1')).toBeNull();
        expect(mockAxiosGet).toBeCalledTimes(0);
        await store.dispatch('code/loadCode', 1);
        expect(mockAxiosGet).toBeCalledTimes(1);

        // The old one should still be in the cache
        mockAxiosGet.mockClear();
        expect(store.getters['code/getCachedCode']('/api/v1/code/-1')).toEqual(buf1);
        await store.dispatch('code/loadCode', -1);
        expect(mockAxiosGet).toBeCalledTimes(0);
    });

    it('should not reinsert old small items', async () => {
        const amount = 10;

        mockAxiosGet.mockReturnValueOnce(Promise.resolve({ data: buf2 }));
        await store.dispatch('code/loadCode', -1);
        mockAxiosGet.mockReturnValue(Promise.resolve({ data: fillBuf(new ArrayBuffer(2 ** 26)) }));

        for (let i = 0; i < amount; ++i) {
            await store.dispatch('code/loadCode', i + 1);
        }

        expect(mockAxiosGet).toBeCalledTimes(amount + 1);

        mockAxiosGet.mockClear();

        // Oldest large one should not be in the cache anymore
        expect(store.getters['code/getCachedCode']('/api/v1/code/1')).toBeNull();
        expect(mockAxiosGet).toBeCalledTimes(0);

        // The oldest very small one should
        expect(store.getters['code/getCachedCode']('/api/v1/code/-1')).toEqual(buf2);
        await store.dispatch('code/loadCode', -1);
        expect(mockAxiosGet).toBeCalledTimes(0);
    });
});
