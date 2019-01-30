/* SPDX-License-Identifier: AGPL-3.0-only */
import DiffViewer from '@/components/DiffViewer';
import * as visualize from '@/utils/visualize';
import { shallowMount, createLocalVue } from '@vue/test-utils';
import VueRouter from 'vue-router';
jest.mock('axios');

visualize.visualizeWhitespace = jest.fn(a => a);

const localVue = createLocalVue();
localVue.use(VueRouter);
const router = new VueRouter();

const text1 = `hello this is original code.

With newlines!`;

const text2 = `hello this is original code.

With newlines!!

more Lines!`;

const text3 = `hello this is original code.

With newlines!!

`;

const text4 = `hello this is original code.

With newlines!!


more Lines!`;

describe('diffCode in DiffViewer.vue', () => {
    const wrapper = shallowMount(DiffViewer, {
        localVue,
        router,
        methods: {
            $hasPermission() { return true; },
            getCode() { return true; },
        },
        propsData: {
            file: { ids: [] },
        },
    });
    const comp = wrapper.vm;
    expect(comp).not.toBe(null);
    expect(comp.lines).toEqual([]);

    it('should be a function', () => {
        expect(typeof comp.diffCode).toBe('function');
    });

    it('should work with equal text', () => {
        visualize.visualizeWhitespace.mockClear();
        comp.diffCode(text1, text1);
        expect(comp.lines.length).toBe(3);
        expect(visualize.visualizeWhitespace.mock.calls.length).toBe(3);
        comp.lines.forEach((line, i) => {
            expect(line.txt).toEqual(text1.split('\n')[i]);
            expect(line.cls).toEqual('');
        });
    });

    it('should work with only deleted code', () => {
        visualize.visualizeWhitespace.mockClear();
        comp.diffCode(text1, '');
        expect(comp.lines.length).toBe(3);
        expect(visualize.visualizeWhitespace.mock.calls.length).toBe(3);
        comp.lines.forEach((line, i) => {
            expect(line.txt).toEqual(text1.split('\n')[i]);
            expect(line.cls).toEqual('removed');
        });
    });

    it('should work with only added code', () => {
        visualize.visualizeWhitespace.mockClear();
        comp.diffCode('', text1);
        expect(comp.lines.length).toBe(3);
        expect(visualize.visualizeWhitespace.mock.calls.length).toBe(3);
        comp.lines.forEach((line, i) => {
            expect(line.txt).toEqual(text1.split('\n')[i]);
            expect(line.cls).toEqual('added');
        });
    });

    it('should work with more edits', () => {
        visualize.visualizeWhitespace.mockClear();
        comp.diffCode(text1, text2);
        expect(comp.lines.length).toBe(6);
        expect(visualize.visualizeWhitespace.mock.calls.length).toBe(6);

        const txt1 = text1.split('\n');
        const txt2 = text2.split('\n');

        expect(comp.lines[0]).toEqual({ txt: txt1[0], cls: '' });
        expect(comp.lines[1]).toEqual({ txt: txt1[1], cls: '' });
        expect(comp.lines[2]).toEqual({ txt: txt1[2], cls: 'removed' });
        expect(comp.lines[3]).toEqual({ txt: txt2[2], cls: 'added' });
        expect(comp.lines[4]).toEqual({ txt: txt2[3], cls: 'added' });
        expect(comp.lines[5]).toEqual({ txt: txt2[4], cls: 'added' });
    });

    it('should work with trailing whitespace', () => {
        visualize.visualizeWhitespace.mockClear();
        comp.diffCode('', text3);
        expect(comp.lines.length).toBe(text3.split('\n').length);
        expect(visualize.visualizeWhitespace.mock.calls.length).toBe(text3.split('\n').length);
        comp.lines.forEach((line, i) => {
            expect(line.txt).toEqual(text3.split('\n')[i]);
            expect(line.cls).toEqual('added');
        });
    });

    it('should work with only whitespace', () => {
        visualize.visualizeWhitespace.mockClear();
        comp.diffCode(text2, text4);
        expect(comp.lines.length).toBe(6);
        expect(visualize.visualizeWhitespace.mock.calls.length).toBe(6);

        const txt1 = text2.split('\n');
        const txt2 = text4.split('\n');

        expect(comp.lines[0]).toEqual({ txt: txt1[0], cls: '' });
        expect(comp.lines[1]).toEqual({ txt: txt1[1], cls: '' });
        expect(comp.lines[2]).toEqual({ txt: txt1[2], cls: '' });
        expect(comp.lines[3]).toEqual({ txt: txt1[3], cls: '' });
        expect(comp.lines[4]).toEqual({ txt: txt2[4], cls: 'added' });
        expect(comp.lines[5]).toEqual({ txt: txt2[5], cls: '' });
    });
});

describe('getChangedParts in DiffViewer.vue', () => {
    let wrapper = shallowMount(DiffViewer, {
        localVue,
        router,
        methods: {
            $hasPermission() { return true; },
            getCode() { return true; },
        },
        propsData: {
            file: { ids: [] },
            context: 2,
        },
    });
    let comp = wrapper.vm;
    expect(comp).not.toBe(null);
    expect(comp.lines).toEqual([]);

    it('should be a function', () => {
        expect(typeof comp.getChangedParts).toBe('function');
    });

    it('should work for empty files', () => {
        comp.lines = [];
        expect(comp.getChangedParts()).toEqual([]);
    });

    it('should work for multiple diffs', () => {
        expect(comp.context).toBe(2);
        comp.lines = [
            { txt: ' 0', cls: '' },
            { txt: ' 1', cls: '' },
            { txt: ' 2', cls: 'added' },
            { txt: ' 3', cls: 'added' },
            { txt: ' 4', cls: 'removed' },
            { txt: ' 5', cls: '' },
            { txt: ' 6', cls: '' },

            { txt: ' 7', cls: '' },
            { txt: ' 8', cls: '' },

            { txt: ' 9', cls: '' },
            { txt: '10', cls: '' },
            { txt: '11', cls: 'added' },
            { txt: '12', cls: 'removed' },
            { txt: '13', cls: '' },
            { txt: '14', cls: '' },

            { txt: '15', cls: '' },
            { txt: '16', cls: '' },

            { txt: '17', cls: '' },
            { txt: '18', cls: '' },
            { txt: '19', cls: 'added' },
            { txt: '20', cls: 'removed' },
            { txt: '21', cls: '' },
            { txt: '22', cls: '' },
            { txt: '23', cls: '' },
            { txt: '24', cls: '' },
            { txt: '25', cls: 'added' },
            { txt: '26', cls: 'deleted' },
        ];
        expect(comp.getChangedParts()).toEqual([
            [0, 7], [9, 15], [17, 27],
        ]);
    });

    it('should have computed property', () => {
        comp.lines = [{ txt: '0', cls: 'added' }];
        expect(comp.changedParts).toEqual([[0, 1]]);
    });
});
