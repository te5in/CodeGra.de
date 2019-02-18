<template>
<b-button :id="btnId"
          class="submit-button"
          :class="`state-${state}`"
          :tabindex="tabindex"
          :disabled="isDisabled"
          :variant="currentVariant"
          :size="size"
          @click="onClick">

    <span class="success-label">
        <slot name="success-label">
            <icon name="check"/>
        </slot>
    </span>
    <span class="warning-label">
        <slot name="warning-label">
            <icon name="warning"/>
        </slot>
    </span>
    <span class="error-label">
        <slot name="error-label">
            <icon name="times"/>
        </slot>
    </span>
    <span class="pending-label">
        <slot name="pending-label">
            <loader :scale="1" center/>
        </slot>
    </span>
    <span class="default-label">
        <slot>
            {{ label }}
        </slot>
    </span>

    <b-popover :placement="popoverPlacement"
               :show="!!error"
               :target="btnId"
               triggers=""
               @hide="onHideError">
        <icon name="times"
              class="hide-button"
              @click.native="hideError"/>

        <span v-if="error">
            <slot name="error" :error="error">
                {{ stringifiedError }}
            </slot>
        </span>
    </b-popover>

    <b-popover :placement="popoverPlacement"
               :show="!!warning"
               :target="btnId"
               triggers=""
               @hide="onHideWarning">
        <icon name="times"
              class="hide-button"
              @click.native="hideWarning"/>

        <span v-if="warning">
            <slot name="warning" :warning="warning">
                {{ warning }}
            </slot>
        </span>
    </b-popover>

    <b-popover v-if="confirm.length > 0"
               :placement="popoverPlacement"
               :show="confirmVisible"
               :target="btnId"
               triggers=""
               @hide="resetConfirm">
        <p>{{ confirm }}</p>

        <b-button-toolbar justify>
            <b-button size="sm"
                      variant="outline-primary"
                      class="confirm-button"
                      @click="acceptConfirm">
                Yes
            </b-button>
            <div class="sep"/>
            <b-button size="sm"
                      variant="primary"
                      class="confirm-button"
                      @click="resetConfirm">
                No
            </b-button>
        </b-button-toolbar>
    </b-popover>
</b-button>
</template>

<script>
import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/times';
import 'vue-awesome/icons/check';
import 'vue-awesome/icons/warning';

import { parseWarningHeader, waitAtLeast } from '@/utils';

import Loader from './Loader';

export const SubmitButtonCancelled = Object.create(Error);

let i = 0;

export default {
    name: 'submit-button',

    props: {
        label: {
            type: String,
            default: 'Submit',
        },

        submit: {
            type: Function,
            required: true,
        },

        filterSuccess: {
            type: Function,
            default: x => x,
        },

        filterError: {
            type: Function,
            default: x => {
                throw x;
            },
        },

        id: {
            type: String,
            default: null,
        },

        tabindex: {
            type: [Number, String],
            default: 0,
        },

        disabled: {
            type: Boolean,
            default: false,
        },

        size: {
            type: String,
            default: 'md',
        },

        variant: {
            type: String,
            default: 'primary',
        },

        duration: {
            type: Number,
            default: 750,
        },

        confirm: {
            type: String,
            default: '',
        },

        popoverPlacement: {
            type: String,
            default: 'top',
        },

        waitAtLeast: {
            type: Number,
            default: 250,
        },
    },

    data() {
        return {
            state: 'default',
            btnId: this.id || `submit-button-${i++}`,
            error: null,
            warning: null,
            response: null,
            confirmVisible: false,
            confirmAccepted: false,
            timeout: null,
        };
    },

    computed: {
        currentVariant() {
            return {
                default: this.variant,
                pending: this.variant,
                success: 'success',
                error: 'danger',
                warning: 'warning',
            }[this.state];
        },

        stringifiedError() {
            let err = this.error;

            if (err == null) {
                return '';
            } else if (err.response && err.response.data) {
                err = err.response.data.message;
            } else if (err instanceof Error) {
                err = err.message;
            } else {
                err = err.toString();
            }

            return err || 'Something unknown went wrong';
        },

        isDisabled() {
            return this.disabled || this.state !== 'default' || this.confirmVisible;
        },
    },

    methods: {
        onClick() {
            if (this.isDisabled) {
                return;
            }

            if (this.confirm) {
                this.showConfirm();
            } else {
                this.doSubmit();
            }
        },

        doSubmit() {
            this.state = 'pending';

            waitAtLeast(this.waitAtLeast, Promise.resolve().then(this.submit))
                .then(this.filterSuccess, this.filterError)
                .then(this.onSuccess, this.onError);
        },

        onSuccess(data, fromWarning = false) {
            if (!fromWarning && data && data.headers && data.headers.warning) {
                this.onWarning(data);
                return;
            }

            this.$emit('success', data);
            this.state = 'success';

            this.timeout = setTimeout(() => {
                this.$emit('after-success', data);
                this.state = 'default';
            }, this.duration);
        },

        onWarning(data) {
            this.$emit('warning', data);
            this.state = 'warning';
            this.warning = parseWarningHeader(data.headers.warning).text;
            this.response = data;
        },

        hideWarning() {
            this.warning = null;
        },

        onHideWarning() {
            this.$emit('after-warning');
            this.state = 'default';
            this.warning = null;

            const res = this.response;
            this.response = null;
            this.onSuccess(res, true);
        },

        onError(err) {
            if (err === SubmitButtonCancelled) {
                this.state = 'default';
                return;
            }

            this.$emit('error', err);
            this.state = 'error';
            this.error = err;
        },

        hideError() {
            this.error = null;
        },

        onHideError() {
            this.$emit('after-error');
            this.state = 'default';
            this.error = null;
        },

        showConfirm() {
            this.state = 'pending';
            this.confirmVisible = true;
        },

        resetConfirm() {
            if (!this.confirmAccepted) {
                this.state = 'default';
            }
            this.confirmVisible = false;
            this.confirmAccepted = false;
        },

        acceptConfirm() {
            this.confirmVisible = false;
            this.confirmAccepted = true;
            this.doSubmit();
        },
    },

    components: {
        Icon,
        Loader,
    },
};
</script>

<style lang="less" scoped>
.submit-button {
    position: relative;
}

.default-label {
    opacity: 0;

    .state-default & {
        opacity: 1;
    }
}

.success-label,
.warning-label,
.error-label,
.pending-label {
    display: none;
    position: absolute;
    top: 50%;
    left: 50%;
    line-height: 1;
    transform: translate(-50%, -50%);
    .fa-icon {
        transform: none;
    }
}

.state-success .success-label,
.state-warning .warning-label,
.state-error .error-label,
.state-pending .pending-label,
.state-default .default-label {
    display: initial;
}

.hide-button {
    float: right;
    cursor: pointer;
    opacity: 0.75;
    margin: 0 0 0.25rem 0.5rem;

    &:hover {
        opacity: 1;
    }
}

.confirm-button {
    flex: 1 1 auto;

    & + .sep {
        width: 0.75rem;
    }
}
</style>

<style lang="less">
.submit-button .loader {
    display: inline-block !important;
}
</style>
