<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<b-button :disabled="pending || disabled"
          class="submit-button"
          :id="btnId"
          :variant="variants[state]"
          :size="size"
          :tabindex="tabindex"
          style="height: 100%;"
          @click="onClick">
    <span v-if="pending">
        <slot name="pending">
            <loader :scale="1" center/>
        </slot>
    </span>
    <span v-else-if="label">{{ label }}</span>
    <slot v-else/>

    <b-popover :show="shouldShowMessage"
               triggers=""
               :target="btnId"
               :placement="popoverPlacement"
               @hide="reset">
        <slot name="error" :messages="err">
            <span>{{ err }}</span>
        </slot>
    </b-popover>

    <b-popover v-if="confirm"
               :show="showConfirm"
               @hide="resetConfirm"
               triggers=""
               :target="btnId"
               :placement="popoverPlacement"
               ref="confirmPopover">
        <p>{{ confirm }}</p>

        <b-button-toolbar justify>
            <b-button variant="danger"
                      size="sm"
                      @click="confirmAction">
                Yes
            </b-button>
            <b-button variant="success"
                      size="sm"
                      @click="resetConfirm">
                No
            </b-button>
        </b-button-toolbar>
    </b-popover>
</b-button>
</template>

<script>
import Loader from './Loader';

let i = 0;

export const SubmitButtonCancelled = Object.create(Error);

export default {
    name: 'submit-button',

    data() {
        return {
            pop: true,
            err: '',
            pending: false,
            state: 'default',
            cancelled: true,
            btnId: this.id || `submitButton-i-${i++}`,
            timeout: null,
            showConfirm: false,
            confirmEvent: null,
            confirmAction: null,
        };
    },

    computed: {
        shouldShowMessage() {
            return (
                this.showError &&
                (this.state === 'failure' || this.state === 'warning') &&
                (Boolean(this.err) || this.showEmpty)
            );
        },

        variants() {
            return {
                default: this.default,
                success: this.success,
                failure: this.failure,
                warning: this.warning,
            };
        },
    },

    props: {
        id: {
            type: String,
            default: null,
        },
        tabindex: {
            default: '0',
        },

        popoverPlacement: {
            type: String,
            default: 'top',
        },
        disabled: {
            type: Boolean,
            default: false,
        },
        label: {
            type: [String, Boolean],
            default: 'Submit',
        },
        size: {
            type: String,
            default: 'md',
        },
        delay: {
            type: Number,
            default: 1000,
        },
        default: {
            type: String,
            default: 'primary',
        },
        success: {
            type: String,
            default: 'success',
        },
        failure: {
            type: String,
            default: 'danger',
        },
        warning: {
            type: String,
            default: 'warning',
        },
        showEmpty: {
            type: Boolean,
            default: true,
        },
        showError: {
            type: Boolean,
            default: true,
        },
        confirm: {
            type: String,
            default: '',
        },
        mult: {
            type: Number,
            default: 1,
        },
    },

    methods: {
        submitFunction(func) {
            if (this.pending) {
                // TODO: We should keep a queue of requests and handle them one after the other,
                // instead of simply rejecting to initiate a request.
                return Promise.reject();
            }

            if (this.confirm && !this.showConfirm) {
                this.$refs.confirmPopover.$emit('open');
                this.showConfirm = true;
                return new Promise(resolve => {
                    this.confirmAction = () => {
                        this.resetConfirm();
                        resolve(this.submitFunction(func));
                    };
                });
            } else {
                return this.submit(func());
            }
        },

        submit(promise) {
            this.pending = true;
            this.cancelled = false;
            return Promise.resolve(promise).then(
                res => !this.cancelled && this.succeed(res),
                err => {
                    if (this.cancelled) {
                        throw SubmitButtonCancelled;
                    } else {
                        return this.fail(err || 'Something unknown went wrong');
                    }
                },
            );
        },

        reset() {
            this.cancelled = true;
            if (this.timeout != null) {
                clearTimeout(this.timeout);
                this.timeout = null;
            }

            this.state = 'default';
            this.err = '';
            this.pending = false;
        },

        succeed(res) {
            this.pending = false;
            return this.update('success').then(() => res);
        },

        cancel() {
            this.cancelled = true;
        },

        warn(err, mult = 3) {
            this.pending = false;
            this.err = err;
            return this.update('warning', mult);
        },

        fail(err, mult = 3) {
            this.pending = false;
            this.err = err;
            return this.update('failure', mult).then(() => {
                throw err;
            });
        },

        update(state, mult = 1) {
            this.state = state;
            return new Promise(resolve => {
                if (this.timeout != null) {
                    clearTimeout(this.timeout);
                }
                if (mult === 0) {
                    resolve();
                    return;
                }
                this.timeout = setTimeout(() => {
                    this.reset();
                    resolve();
                }, this.delay * mult);
            });
        },

        onClick(event) {
            if (this.pending) {
                return;
            }
            if (this.confirm && !this.showConfirm) {
                event.stopImmediatePropagation();
                this.$refs.confirmPopover.$emit('open');
                this.showConfirm = true;
                this.confirmAction = this.onClick;
                this.confirmEvent = event;
            } else {
                this.$emit('click', this.confirmEvent || event);
                this.resetConfirm();
            }
        },

        resetConfirm() {
            this.showConfirm = false;
            this.confirmAction = null;
            this.confirmEvent = null;
        },
    },

    components: {
        Loader,
    },
};
</script>

<style lang="less" scoped>
.btn-toolbar {
    width: 60%;
    margin: 0 auto;
}

.btn .fa-icon {
    margin-right: 0 !important;
}

.loader {
    padding: 0.25em 0;
}
</style>
