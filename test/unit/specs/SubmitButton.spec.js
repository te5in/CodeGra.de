/* SPDX-License-Identifier: AGPL-3.0-only */
import SubmitButton from '@/components/SubmitButton';
import { shallowMount, createLocalVue } from '@vue/test-utils';
import BootstrapVue from 'bootstrap-vue'

jest.mock('axios');

const localVue = createLocalVue();
localVue.use(BootstrapVue);

function timedPromise(timeout) {
    return new Promise(resolve => setTimeout(resolve, timeout));
}

describe('SubmitButton.vue', () => {
    let wrapper;
    let comp;
    let mockSubmit;

    function mount(props) {
        let submit = 'success';
        if (props && props.submit) {
            submit = props.submit;
            delete props.submit;
        }

        if (submit === 'success') {
            mockSubmit = jest.fn(() => Promise.resolve('success'));
        } else if (submit === 'warning') {
            mockSubmit = jest.fn(() =>
                Promise.resolve({ data: { headers: { warning: 'warning' } } }),
            );
        } else if (submit === 'error') {
            mockSubmit = jest.fn(() => Promise.reject(new Error('error')));
        } else {
            mockSubmit = submit;
        }

        wrapper = shallowMount(SubmitButton, {
            localVue,
            propsData: Object.assign({
                submit: mockSubmit,
                waitAtLeast: 0,
            }, props),
        });

        comp = wrapper.vm;
    }

    beforeEach(() => mount());

    it('should not be null', () => {
        expect(comp).not.toBe(null);
    });

    describe('the button state', () => {
        it('should be "default" by default', () => {
            expect(comp.state).toBe('default');
        });

        it('should be "pending" right after starting a request', async () => {
            comp.onClick();
            await comp.$nextTick();
            expect(comp.state).toBe('pending');
            expect(mockSubmit).toBeCalledTimes(1);

            mount({ submit: 'error' });
            comp.onClick();
            await comp.$nextTick();
            expect(comp.state).toBe('pending');
            expect(mockSubmit).toBeCalledTimes(1);
        });

        it('should be "success" after a successful request', async () => {
            let promise;
            mount({ submit: jest.fn(() => {
                promise = Promise.resolve('success');
                return promise;
            }) });
            comp.onClick();
            expect(comp.state).not.toBe('success');

            await comp.$nextTick();
            expect(mockSubmit).toBeCalledTimes(1);

            await promise;
            await timedPromise(100);
            expect(comp.state).toBe('success');
            expect(wrapper.emitted().success).toHaveLength(1);
            expect(wrapper.emitted()['after-success']).toBeUndefined();

            await timedPromise(comp.duration / 2);
            expect(comp.state).toBe('success');

            await timedPromise(comp.duration);
            expect(comp.state).toBe('default');
            expect(wrapper.emitted()['after-success']).toHaveLength(1);
        });

        it('should be "warning" after a request returns a warning', async () => {
            const warning = { headers: { warning: 'warning' } };

            let promise;
            mount({ submit: jest.fn(() => {
                promise = Promise.resolve(warning);
                return promise;
            }) });
            comp.onClick();
            expect(comp.state).not.toBe('warning');

            await comp.$nextTick();
            expect(mockSubmit).toBeCalledTimes(1);

            await promise;
            await timedPromise(100);
            expect(comp.state).toBe('warning');
            expect(wrapper.emitted().warning).toHaveLength(1);
            expect(wrapper.emitted()['after-warning']).toBeUndefined();

            comp.onHideWarning();
            await timedPromise(100);

            expect(comp.state).toBe('success');
            expect(wrapper.emitted()['after-warning']).toHaveLength(1);
        });

        it('should be "error" after a failed request', async () => {
            let promise;
            mount({ submit: jest.fn(() => {
                promise = Promise.reject('error');
                return promise;
            }) });
            comp.onClick();
            expect(comp.state).not.toBe('error');

            await comp.$nextTick();
            expect(mockSubmit).toBeCalledTimes(1);

            let caught = 0;
            try {
                await promise;
            } catch (e) {
                caught = 1;
            }
            expect(caught).toBe(1);

            await timedPromise(100);
            expect(comp.state).toBe('error');
            expect(wrapper.emitted().error).toHaveLength(1);
            expect(wrapper.emitted()['after-error']).toBeUndefined();

            comp.onHideError();
            await timedPromise(100);

            expect(comp.state).toBe('default');
            expect(wrapper.emitted()['after-error']).toHaveLength(1);
        });
    });

    describe('the confirm popover', () => {
        beforeEach(() => {
            mount({
                confirm: 'confirm message',
            });
            comp.onClick();
        });

        it('should delay triggering of the submit action', async () => {
            expect(comp.state).toBe('pending');
            expect(comp.confirmVisible).toBe(true);

            await timedPromise(comp.duration);

            expect(comp.state).toBe('pending');
            expect(comp.confirmVisible).toBe(true);
        });

        it('should trigger submission after it has been confirmed', async () => {
            expect(comp.confirmVisible).toBe(true);
            comp.acceptConfirm();

            comp.$nextTick().then(() => {
                expect(comp.confirmVisible).toBe(false);
                expect(comp.confirmAccepted).toBe(true);
                expect(comp.state).toBe('success');
            });
        });

        it('should reset when it has been cancelled', async() => {
            expect(comp.confirmVisible).toBe(true);
            comp.resetConfirm();

            comp.$nextTick().then(() => {
                expect(comp.confirmVisible).toBe(false);
                expect(comp.confirmAccepted).toBe(false);
                expect(comp.state).toBe('default');
            });
        });
    });
});
