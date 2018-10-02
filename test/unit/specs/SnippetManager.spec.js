import SnippetManager from '@/components/SnippetManager';
import { shallowMount, createLocalVue } from '@vue/test-utils';
import VueRouter from 'vue-router';
import Vuex from 'vuex';
import BootstrapVue from 'bootstrap-vue'

jest.mock('axios');

const localVue = createLocalVue();
localVue.use(Vuex);
localVue.use(BootstrapVue);

const snippets = {
    duplicate: { id: 0, key: 'duplicate', value: 'duplicate' },
};

describe('SnippetManager.vue', () => {
    let store;
    let wrapper;
    let comp;
    let mockRefresh;
    let mockAdd;
    let mockUpdate;
    let mockRemove;
    let mockPut;
    let mockPatch;
    let mockDelete;
    let mockSubmit;
    let mockFail;

    function snippetIndex(snippet) {
        return comp.allSnippets.indexOf(snippet);
    }

    beforeEach(() => {
        mockRefresh = jest.fn(() => Promise.resolve(true));
        mockAdd = jest.fn();
        mockUpdate = jest.fn();
        mockRemove = jest.fn();
        mockPut = jest.fn(() => Promise.resolve(true));
        mockPatch = jest.fn(() => Promise.resolve(true));
        mockDelete = jest.fn(() => Promise.resolve(true));
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
                        deleteSnippet: mockRemove,
                    },
                    namespaced: true,
                },
            },
        });

        wrapper = shallowMount(SnippetManager, {
            store,
            localVue,
            mocks: {
                $http: {
                    put: mockPut,
                    patch: mockPatch,
                    delete: mockDelete,
                },
            },
        });

        comp = wrapper.vm;
    });

    it('should not be null', () => {
        expect(comp).not.toBe(null);
    });

    describe('the newSnippets array', () => {
        it('should be an array with a single item after mount', () => {
            expect(comp.newSnippets).toBeInstanceOf(Array);
            expect(comp.newSnippets.length).toBe(1);
        });

        it('should have all its items appear in allSnippets', () => {
            comp.newSnippets.concat([
                comp.makeSnippet(),
                comp.makeSnippet(),
                comp.makeSnippet(),
            ]);

            for (let snippet of comp.newSnippets) {
                expect(snippetIndex(snippet)).toBeGreaterThan(-1);
            }
        });

        it('should add a new snippet when the last empty snippet changes', () => {
            comp.snippetKeyChanged(comp.newSnippets[0], 'key');
            expect(comp.newSnippets.length).toBe(2);
            comp.snippetValueChanged(comp.newSnippets[0], 'value');
            expect(comp.newSnippets.length).toBe(2);
        });

        it('should add a new snippet when the last item is removed', () => {
            comp.newSnippets.splice(0, comp.newSnippets.length);
            expect(comp.newSnippets.length).toBe(1);
        });
    });

    describe('saveButtonPopover', () => {
        it('should return the correct message if the snippet key is invalid', () => {
            const snippet = comp.newSnippets[0];
            comp.snippetKeyChanged(snippet, '');
            comp.snippetValueChanged(snippet, 'value');
            expect(comp.saveButtonPopover(snippet)).toMatch(comp.errorMessages.emptyKey);
        });

        it('should return the correct message if the snippet value is invalid', () => {
            const snippet = comp.newSnippets[0];
            comp.snippetKeyChanged(snippet, 'key');
            comp.snippetValueChanged(snippet, '');
            expect(comp.saveButtonPopover(snippet)).toMatch(comp.errorMessages.emptyValue);
        });

        it('should return the correct message if both the snippet value and key are invalid', () => {
            const snippet = comp.newSnippets[0];
            comp.snippetKeyChanged(snippet, '');
            comp.snippetValueChanged(snippet, '');
            expect(comp.saveButtonPopover(snippet)).toMatch(comp.errorMessages.emptyKey);
            expect(comp.saveButtonPopover(snippet)).toMatch(comp.errorMessages.emptyValue);
        });

        it('should return the correct message the snippet is unchanged', () => {
            const snippet = comp.newSnippets[0];
            snippet.origKey = 'key';
            snippet.origValue = 'value';
            comp.resetSnippet(snippet);
            expect(comp.hasSnippetChanged(snippet)).toBe(false);
            expect(comp.saveButtonPopover(snippet)).toMatch(comp.errorMessages.unchangedSnippet);
        });

        it('should return the correct message the snippet has unsaved changes', () => {
            const snippet = comp.newSnippets[0];
            comp.snippetKeyChanged(snippet, 'key');
            comp.snippetValueChanged(snippet, 'value');
            expect(comp.hasSnippetChanged(snippet)).toBe(true);
            expect(comp.saveButtonPopover(snippet)).toMatch(comp.errorMessages.unsavedChanges);
        });
    });

    describe('snippetKeyChanged', () => {
        const validKeys = [
            'validkey',
            'validKey',
            'valid_key',
            'valid-key',
            'validkey?',
            '#validkey',
        ];
        const invalidSpaces = [
            'key with spaces',
            'key\twith\ttabs',
        ];
        const invalidEmpty = [''];
        const invalidDuplicate = ['duplicate'];

        it('should be a function', () => {
            expect(typeof comp.snippetKeyChanged).toBe('function');
        });

        it('should always change the key attribute', () => {
            const snippet = comp.newSnippets[0];
            const keys = validKeys.concat(invalidSpaces, invalidEmpty, invalidDuplicate);

            for (let key of keys) {
                comp.snippetKeyChanged(snippet, key);
                expect(snippet.key).toBe(key);
            }
        });

        it('should not reject valid keys', () => {
            const snippet = comp.newSnippets[0];

            for (let key of validKeys) {
                comp.snippetKeyChanged(snippet, key);
                expect(snippet.keyError).toBe('');
            }
        });

        it('should reject a key with spaces', () => {
            const snippet = comp.newSnippets[0];

            for (let key of invalidSpaces) {
                comp.snippetKeyChanged(snippet, key);
                expect(snippet.keyError).toBe(comp.errorMessages.spacesInKey);
            }
        });

        it('should reject an empty key', () => {
            const snippet = comp.newSnippets[0];

            for (let key of invalidEmpty) {
                comp.snippetKeyChanged(snippet, key);
                expect(snippet.keyError).toBe(comp.errorMessages.emptyKey);
            }
        });

        it('should reject a duplicate key', () => {
            const snippet = comp.newSnippets[0];

            for (let key of invalidDuplicate) {
                comp.snippetKeyChanged(snippet, key);
                expect(snippet.keyError).toBe(comp.errorMessages.duplicateKey);
            }
        });
    });

    describe('snippetValueChanged', () => {
        const validValues = [
            'value',
            'value with spaces',
            'value\twith\ttabs',
            'duplicate',
        ];
        const invalidValues = [''];

        it('should be a function', () => {
            expect(typeof comp.snippetValueChanged).toBe('function');
        });

        it('should always change the value attribute', () => {
            const snippet = comp.newSnippets[0];
            const values = validValues.concat(invalidValues);
            for (let value of values) {
                comp.snippetValueChanged(snippet, value);
                expect(snippet.value).toBe(value);
            }
        });

        it('should not reject valid values', () => {
            const snippet = comp.newSnippets[0];
            for (let value of validValues) {
                comp.snippetValueChanged(snippet, value);
                expect(snippet.valueError).toBe('');
            }
        });

        it('should reject an empty value', () => {
            const snippet = comp.newSnippets[0];
            for (let value of invalidValues) {
                comp.snippetValueChanged(snippet, value);
                expect(snippet.valueError).toBe(comp.errorMessages.emptyValue);
            }
        });
    });

    describe('saveSnippet', () => {
        it('should be a function', () => {
            expect(typeof comp.snippetValueChanged).toBe('function');
        });

        it('should not save if the snippet hasn\'t changed', async () => {
            for (let i = 0; i < comp.allSnippets.length; i++) {
                const snippet = comp.allSnippets[i];
                comp.$refs = { [`snippetSaveButton-${i}`]: { fail: mockFail } };
                comp.snippetKeyChanged(snippet, snippet.origKey);
                comp.snippetValueChanged(snippet, snippet.origValue);
                await comp.saveSnippet(snippet, i);
            }

            expect(mockFail).toBeCalledTimes(comp.allSnippets.length);
            expect(mockAdd).toBeCalledTimes(0);
            expect(mockUpdate).toBeCalledTimes(0);
            expect(mockPut).toBeCalledTimes(0);
            expect(mockPatch).toBeCalledTimes(0);
            expect(mockSubmit).toBeCalledTimes(0);
        });

        it('should not save if the snippet has an invalid key or value', async () => {
            const snippet = comp.newSnippets[0];
            const index = snippetIndex(snippet);
            comp.$refs = { [`snippetSaveButton-${index}`]: { fail: mockFail } };
            comp.snippetKeyChanged(snippet, '');
            comp.snippetValueChanged(snippet, 'value');
            await comp.saveSnippet(snippet, index);

            comp.snippetKeyChanged(snippet, 'key');
            comp.snippetValueChanged(snippet, '');
            await comp.saveSnippet(snippet, index);

            expect(mockFail).toBeCalledTimes(2);
            expect(mockAdd).toBeCalledTimes(0);
            expect(mockUpdate).toBeCalledTimes(0);
            expect(mockPut).toBeCalledTimes(0);
            expect(mockPatch).toBeCalledTimes(0);
            expect(mockSubmit).toBeCalledTimes(0);
        });

        it('should add a new snippet if the snippet has no id', async () => {
            const snippet = comp.newSnippets[0];
            const index = snippetIndex(snippet);
            comp.$refs = { [`snippetSaveButton-${index}`]: { submit: mockSubmit } }
            snippet.id = null;
            comp.snippetKeyChanged(snippet, 'key');
            comp.snippetValueChanged(snippet, 'value');
            await comp.saveSnippet(snippet, index);

            expect(mockAdd).toBeCalledTimes(1);
            expect(mockUpdate).toBeCalledTimes(0);
            expect(mockPut).toBeCalledTimes(1);
            expect(mockPatch).toBeCalledTimes(0);
            expect(mockSubmit).toBeCalledTimes(1);

            const newSnippet = comp.newSnippets[0];
            expect(newSnippet.key).toBe('');
            expect(newSnippet.value).toBe('');
        });

        it('should update a snippet if the snippet has an id', async () => {
            comp.$refs = { ['snippetSaveButton-0']: { submit: mockSubmit } }

            const snippet = comp.allSnippets[0];
            comp.snippetKeyChanged(snippet, 'key');
            comp.snippetValueChanged(snippet, 'value');
            await comp.saveSnippet(snippet, 0);

            expect(mockAdd).toBeCalledTimes(0);
            expect(mockUpdate).toBeCalledTimes(1);
            expect(mockPut).toBeCalledTimes(0);
            expect(mockPatch).toBeCalledTimes(1);
            expect(mockSubmit).toBeCalledTimes(1);
        });
    });

    describe('deleteSnippet', () => {
        it('should be a function', () => {
            expect(typeof comp.snippetKeyChanged).toBe('function');
        });

        it('should not delete the last empty snippet', async () => {
            let snippet = comp.newSnippets[0];
            await comp.deleteSnippet(snippet, snippetIndex(snippet));
            expect(comp.newSnippets[0]).toBe(snippet);

            comp.snippetKeyChanged(snippet, 'key');
            snippet = comp.newSnippets[1];
            comp.deleteSnippet(snippet, snippetIndex(snippet));
            expect(comp.newSnippets[1]).toBe(snippet);
        });

        it('should delete an unsaved snippet if it is not the last one', async () => {
            const snippet = comp.newSnippets[0];
            comp.snippetKeyChanged(snippet, 'key');
            comp.snippetKeyChanged(snippet, '');
            await comp.deleteSnippet(snippet, snippetIndex(snippet));
            expect(comp.newSnippets.length).toBe(1);
        });

        it('should delete a snippet with an id from the store', async () => {
            comp.$refs = { ['snippetDeleteButton-0']: { submit: mockSubmit } };

            const snippet = comp.allSnippets[0];
            comp.snippetKeyChanged(snippet, 'key');
            await comp.deleteSnippet(snippet, snippetIndex(snippet));
            expect(mockRemove).toBeCalledTimes(1);
            expect(mockDelete).toBeCalledTimes(1);
            expect(mockSubmit).toBeCalledTimes(1);
        });
    });

    describe('resetSnippet', () => {
        it('should be a function', () => {
            expect(typeof comp.snippetKeyChanged).toBe('function');
        });

        it('should reset the snippet\'s key, value, keyError and valueError', () => {
            let snippet = comp.newSnippets[0];
            comp.snippetKeyChanged(snippet, 'key');
            comp.snippetValueChanged(snippet, 'value');
            expect(snippet.key).not.toBe(snippet.origKey);
            expect(snippet.value).not.toBe(snippet.origValue);

            comp.resetSnippet(snippet);
            expect(snippet.key).toBe(snippet.origKey);
            expect(snippet.value).toBe(snippet.origValue);
        });
    });
});
