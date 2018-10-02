import FeedbackArea from '@/components/FeedbackArea';
import { shallowMount, createLocalVue } from '@vue/test-utils';
import VueRouter from 'vue-router';
import Vuex from 'vuex';
import BootstrapVue from 'bootstrap-vue'

jest.mock('axios');

const localVue = createLocalVue();
localVue.use(Vuex);
localVue.use(BootstrapVue);

const snippets = {
    snippet: { id: 0, key: 'snippet', value: 'snippet expanded text' },
};

describe('FeedbackArea.vue', () => {
    let store;
    let wrapper;
    let comp;
    let mockRefresh;
    let mockAdd;
    let mockUpdate;
    let mockPut;
    let mockPatch;
    let mockSubmit;
    let mockFail;

    function makeInstance(propsData = null) {
        wrapper = shallowMount(FeedbackArea, {
            store,
            localVue,
            methods: {
                $hasPermission() { return true; },
            },
            mocks: {
                $http: {
                    put: mockPut,
                    patch: mockPatch,
                },
            },
            propsData: Object.assign({
                line: 0,
                feedback: '',
                fileId: 0,
            }, propsData),
        });

        comp = wrapper.vm;
    }

    beforeEach(() => {
        mockRefresh = jest.fn(() => Promise.resolve(true));
        mockAdd = jest.fn();
        mockUpdate = jest.fn();
        mockPut = jest.fn(() => Promise.resolve(true));
        mockPatch = jest.fn(() => Promise.resolve(true));
        mockSubmit = jest.fn(() => Promise.resolve(true));
        mockFail = jest.fn(() => Promise.resolve(false));

        store = new Vuex.Store({
            modules: {
                user: {
                    state: {
                        snippets,
                    },
                    getters: {
                        snippets: () => snippets,
                    },
                    actions: {
                        refreshSnippets: mockRefresh,
                        addSnippet: mockAdd,
                        updateSnippet: mockUpdate,
                    },
                    namespaced: true,
                },
            },
        });

        makeInstance({ canUseSnippets: true });
    });

    it('should not be null', () => {
        expect(comp).not.toBe(null);
    });

    describe('expandSnippet', () => {
        const event = { preventDefault: () => {} };

        it('should do nothing if the user can\'t use snippets', () => {
            makeInstance({ canUseSnippets: false });

            const snippet = Object.keys(snippets)[0];
            comp.canUseSnippets = false;
            comp.internalFeedback = snippet;
            comp.expandSnippet(event);
            expect(comp.internalFeedback).toBe(snippet);
        });

        it('should do nothing if some text is selected', () => {
            const snippet = Object.keys(snippets)[0];
            comp.$refs.field = { selectionStart: 0, selectionEnd: 2 };
            comp.internalFeedback = snippet;
            comp.expandSnippet(event);
            expect(comp.internalFeedback).toBe(snippet);
        });

        it('should do nothing if the last word is not a snippet', () => {
            let values = [
                'nonexisting',
                'this snippet is nonexisting',
                `multiline text

                this snippet is nonexisting`,
                'nonexisting-snippet',
            ];
            let field = {};
            comp.$refs.field = field;

            for (let value of values) {
                field.selectionStart = value.length;
                field.selectionEnd = value.length;
                comp.internalFeedback = value;
                comp.expandSnippet(event);
                expect(comp.internalFeedback).toBe(value);
            }
        });

        it('should expand the last word if it is a snippet', () => {
            let values = [
                'snippet',
                'this is a snippet',
                `multiline text

                ending in a snippet`,
            ];
            let field = {};
            comp.$refs.field = field;

            for (let value of values) {
                field.selectionStart = value.length;
                field.selectionEnd = value.length;
                comp.internalFeedback = value;
                comp.expandSnippet(event);
                expect(comp.internalFeedback).toBe(
                    value.replace(/snippet$/, snippets.snippet.value),
                );
            }
        });
    });

    describe('addSnippet', () => {
        beforeEach(() => {
            comp.$refs.addSnippetButton = {
                fail: mockFail,
                submit: mockSubmit,
            };
        });

        it('should fail if the snippet key is invalid', async () => {
            comp.snippetKey = 'key with spaces';
            comp.internalFeedback = 'feedback';
            await comp.addSnippet();
            comp.snippetKey = '';
            await comp.addSnippet();
            expect(mockFail).toBeCalledTimes(2);
            expect(mockSubmit).toBeCalledTimes(0);
        });

        it('should fail if the feedback is empty', async () => {
            comp.snippetKey = 'key';
            comp.internalFeedback = '';
            await comp.addSnippet();
            expect(mockFail).toBeCalledTimes(1);
            expect(mockSubmit).toBeCalledTimes(0);
        });

        it('should update a snippet if the key already exists', async () => {
            comp.snippetKey = 'snippet';
            comp.internalFeedback = 'new value';
            await comp.addSnippet();
            expect(mockFail).toBeCalledTimes(0);
            expect(mockAdd).toBeCalledTimes(0);
            expect(mockPut).toBeCalledTimes(0);
            expect(mockUpdate).toBeCalledTimes(1);
            expect(mockPatch).toBeCalledTimes(1);
            expect(mockSubmit).toBeCalledTimes(1);
        });

        it('should add a new snippet if the key doesn\'t exist', async () => {
            comp.snippetKey = 'new_snippet';
            comp.internalFeedback = 'new value';
            await comp.addSnippet();
            expect(mockFail).toBeCalledTimes(0);
            expect(mockAdd).toBeCalledTimes(1);
            expect(mockPut).toBeCalledTimes(1);
            expect(mockUpdate).toBeCalledTimes(0);
            expect(mockPatch).toBeCalledTimes(0);
            expect(mockSubmit).toBeCalledTimes(1);
        });
    });

    describe('findSnippet', () => {
        beforeEach(() => {
            comp.$refs.snippetDialog = { show: false };
        });

        it('should do nothing if the field already has a value', () => {
            comp.snippetKey = 'new_snippet';
            comp.internalFeedback = Object.values(snippets)[0].value;
            comp.findSnippet();
            expect(comp.snippetKey).toBe('new_snippet');
        });

        it('should do nothing if the snippet dialog is visible', () => {
            comp.$refs.snippetDialog.show = true;
            comp.snippetKey = '';
            comp.internalFeedback = Object.values(snippets)[0].value;
            comp.findSnippet();
            expect(comp.snippetKey).toBe('');
        });

        it('should do nothing if the value in internalFeedback doesn\'t have a corresponding snippet', () => {
            comp.snippetKey = '';
            comp.internalFeedback = 'no snippet with this text';
            comp.findSnippet();
            expect(comp.snippetKey).toBe('');
        });

        it('should set the snippet key corresponding to the value in internalFeedback', () => {
            const [key, { value }] = Object.entries(snippets)[0];
            comp.snippetKey = '';
            comp.internalFeedback = value;
            comp.findSnippet();
            expect(comp.snippetKey).toBe(key);
        });
    });
});
