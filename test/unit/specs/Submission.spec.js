/* SPDX-License-Identifier: AGPL-3.0-only */
import Submission from '@/pages/Submission';
import { shallowMount, createLocalVue } from '@vue/test-utils';
import VueRouter from 'vue-router';
jest.mock('axios');

const localVue = createLocalVue();
localVue.use(VueRouter);
const router = new VueRouter();

function jsonCopy(src) {
    return JSON.parse(JSON.stringify(src));
}

const tree1 = {
    name: 'root1',
    id: 1,
    entries: [
        {
            name: 'file1',
            id: 2,
        },
        {
            name: 'sub1',
            id: 3,
            entries: [{ name: 'file2', id: 4 }],
        },
    ],
};


const tree2 = jsonCopy(tree1);
tree2.entries.splice(0, 1);
tree2.entries[0].entries[0].id = 5;
tree2.entries[0].entries.push({ name: 'file3', id: 6 });

const tree3 = jsonCopy(tree1);
tree3.entries.push({
    name: 'sub2',
    id: 4,
    entries: [{
        name: 'file4',
        id: 7,
    }],
});

const tree4 = jsonCopy(tree1);
tree4.entries.splice(1, 1);
tree4.entries.push({
    name: 'sub1',
    id: 8,
});

describe('matchFiles in Submission.vue', () => {
    const wrapper = shallowMount(Submission, {
        localVue,
        router,
        mocks: {
            $hasPermission() { return true; },
        },
    });
    const comp = wrapper.vm;

    it('should be a function', () => {
        expect(typeof comp.matchFiles).toBe('function');
    });

    it('should work with two identical trees', () => {
        expect(comp.matchFiles(tree1, tree1)).toEqual({
            name: 'root1',
            entries: [
                {
                    name: 'file1',
                    ids: [2, 2],
                },
                {
                    name: 'sub1',
                    entries: [{ name: 'file2', ids: [4, 4] }],
                },
            ],
        });
        // No revision should be added
        expect(tree1.entries[0]).toEqual({
            name: 'file1',
            id: 2,
            revision: undefined,
        });
    });

    it('should work with a modified tree', () => {
        expect(comp.matchFiles(tree1, tree2)).toEqual({
            name: 'root1',
            entries: [
                {
                    name: 'file1',
                    ids: [2, null],
                },
                {
                    name: 'sub1',
                    entries: [
                        { name: 'file2', ids: [4, 5] },
                        { name: 'file3', ids: [null, 6] },
                    ],
                },
            ],
        });
        expect(tree1.entries[0]).toEqual({
            name: 'file1',
            id: 2,
            revision: null,
        });
        expect(tree1.entries[1]).toEqual({
            entries: [{ name: 'file2', id: 4, revision: expect.any(Object) }],
            name: 'sub1',
            id: 3,
        });
    });

    it('should work with a inserted directory', () => {
        expect(comp.matchFiles(tree1, tree3)).toEqual({
            name: 'root1',
            entries: [
                {
                    name: 'file1',
                    ids: [2, 2],
                },
                {
                    name: 'sub1',
                    entries: [{ name: 'file2', ids: [4, 4] }],
                },
                {
                    name: 'sub2',
                    entries: [{ name: 'file4', ids: [null, 7] }],
                },
            ],
        });
    });

    it('should work when replacing a directory with a file', () => {
        expect(comp.matchFiles(tree1, tree4)).toEqual({
            name: 'root1',
            entries: [
                {
                    name: 'file1',
                    ids: [2, 2],
                },
                {
                    name: 'sub1',
                    entries: [{ name: 'file2', ids: [4, null] }],
                },
                {
                    name: 'sub1',
                    ids: [null, 8],
                },
            ],
        });
        expect(tree1.entries[1]).toEqual({
            entries: expect.any(Array),
            name: 'sub1',
            revision: expect.any(Object),
            id: 3,
        });
    });

    it('should work when replacing a file with a directory', () => {
        expect(comp.matchFiles(tree4, tree1)).toEqual({
            name: 'root1',
            entries: [
                {
                    name: 'file1',
                    ids: [2, 2],
                },
                {
                    name: 'sub1',
                    entries: [{ name: 'file2', ids: [null, 4] }],
                },
                {
                    name: 'sub1',
                    ids: [8, null],
                },
            ],
        });
        expect(tree4.entries[1]).toEqual({
            name: 'sub1',
            revision: expect.any(Object),
            id: 8,
        });
    });
});
