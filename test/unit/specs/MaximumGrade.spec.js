import MaximumGrade from '@/components/MaximumGrade';
import BootstrapVue from 'bootstrap-vue';
import { shallowMount, createLocalVue } from '@vue/test-utils';
import VueRouter from 'vue-router';
import Vuex from 'vuex';

jest.mock('axios');

const localVue = createLocalVue();
localVue.use(VueRouter);
const router = new VueRouter();

localVue.use(Vuex);

localVue.use(BootstrapVue);

describe('MaximumGrade.vue', () => {
    let store;
    let wrapper;
    let mockPatch;
    let mockSubmit;
    let mockUpdate;

    beforeEach(() => {
        mockUpdate = jest.fn();
        mockPatch = jest.fn(() => Promise.resolve(true));
        mockSubmit = jest.fn(() => Promise.resolve(true));

        store = new Vuex.Store({
            modules: {
                courses: {
                    state: { },
                    getters: { assignments: () => ({ '-1': { id: -1 } }) },
                    actions: { updateAssignment: mockUpdate },
                    namespaced: true,
                },
            },
        });

        wrapper = shallowMount(MaximumGrade, {
            store,
            localVue,
            router,
            methods: {
                $hasPermission() { return true; },
            },
            mocks: {
                $http: { patch: mockPatch },
            },
            propsData: {
                assignmentId: -1,
            },
        });
    });

    describe('submit', () => {
        it('should be a function', () => {
            const comp = wrapper.vm;
            expect(comp).not.toBe(null);

            expect(typeof comp.submit).toBe('function');
        });

        it('should work when deleting max grade', async () => {
            const comp = wrapper.vm;
            comp.maxGrade = '';
            expect(mockUpdate.mock.calls.length).toBe(0);
            await comp.submit({ submit: mockSubmit });
            expect(mockPatch).toBeCalledTimes(1);
            expect(mockPatch).toBeCalledWith('/api/v1/assignments/-1', { max_grade: null });

            expect(mockSubmit).toBeCalledTimes(1);

            expect(mockUpdate).toBeCalledTimes(1);
            expect(mockUpdate).toBeCalledWith(
                expect.any(Object),
                {
                    assignmentId: -1,
                    assignmentProps: { max_grade: null },
                },
                undefined,
            );
        });

        it('should work when setting a max grade', async () => {
            const comp = wrapper.vm;
            comp.maxGrade = '12';
            await comp.submit({ submit: mockSubmit });

            expect(mockPatch).toBeCalledTimes(1);
            expect(mockPatch).toBeCalledWith('/api/v1/assignments/-1', { max_grade: 12 });

            expect(mockSubmit).toBeCalledTimes(1);

            expect(mockUpdate).toBeCalledTimes(1);
            expect(mockUpdate).toBeCalledWith(
                expect.any(Object),
                {
                    assignmentId: -1,
                    assignmentProps: { max_grade: 12 },
                },
                undefined,
            );
        });

        it('should work when api throws', async () => {
            const comp = wrapper.vm;
            comp.maxGrade = '';
            mockPatch.mockReturnValue(Promise.reject({ response: { data: { message: 'ERR!' } } }));
            expect(mockUpdate.mock.calls.length).toBe(0);
            await comp.submit({ submit: mockSubmit });

            expect(mockPatch).toBeCalledTimes(1);
            expect(mockPatch).toBeCalledWith('/api/v1/assignments/-1', { max_grade: null });

            expect(mockSubmit).toBeCalledTimes(1);
            await expect(mockSubmit.mock.calls[0][0]).rejects.toMatch('ERR!');

            expect(mockUpdate).toBeCalledTimes(0);
        });
    });

    describe('reset', () => {
        it('should call submit', () => {
            const comp = wrapper.vm;
            const obj = {};
            const obj2 = {};
            const mock = jest.fn();

            comp.maxGrade = obj;
            comp.submit = mock;
            comp.$refs = { resetButton: obj2 };

            comp.reset();

            expect(mock).toBeCalledTimes(1);
            expect(mock).toBeCalledWith(obj2);
            expect(comp.maxGrade).toBe(null);
        });
    });
});
