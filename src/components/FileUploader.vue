<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<b-form-fieldset class="file-uploader" :class="{ disabled }">
    <b-input-group>
        <b-input-group-prepend>
            <submit-button :disabled="this.file === null"
                           :id="buttonId"
                           class="file-uploader-button"
                           :confirm="confirm"
                           :submit="submit"
                           :filter-error="maybeCancelSubmit"
                           @success="$emit('response', $event)"
                           @after-success="clearForm"/>
        </b-input-group-prepend>
        <b-input-group-prepend v-if="$slots.default">
            <slot/>
        </b-input-group-prepend>
        <b-form-file class="file-uploader-form"
                     ref="formFile"
                     name="file"
                     placeholder="Click here to choose a file..."
                     v-model="file"
                     :disabled="disabled"/>
    </b-input-group>
</b-form-fieldset>
</template>

<script>
import SubmitButton, { SubmitButtonCancelled } from './SubmitButton';

export default {
    name: 'file-uploader',

    props: {
        url: {
            type: String,
            default: '',
        },
        disabled: {
            type: Boolean,
            default: false,
        },
        confirm: {
            type: String,
            default: '',
        },
        maybeHandleError: {
            type: Function,
            default: () => false,
        },
        buttonId: {
            default: undefined,
        },
    },

    data() {
        return {
            file: null,
        };
    },

    computed: {
        requestData() {
            const fdata = new FormData();
            fdata.append('file', this.file);
            return fdata;
        },
    },

    methods: {
        submit() {
            if (this.disabled) {
                throw new Error('This uploader is disabled');
            }

            return this.$http.post(this.url, this.requestData);
        },

        maybeCancelSubmit(err) {
            if (this.maybeHandleError(err)) {
                this.$emit('error', err);
                throw SubmitButtonCancelled;
            } else {
                throw err;
            }
        },

        clearForm() {
            this.$emit('clear');
            if (this.$refs.formFile) {
                this.$refs.formFile.reset();
            }
        },
    },

    components: {
        SubmitButton,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.form-group {
    margin-bottom: 0;
}

.disabled,
:disabled {
    cursor: not-allowed !important;
}

.file-uploader-button {
    height: 100%;

    button {
        height: 100%;
    }
}
</style>

<style lang="less">
@import '~mixins.less';

.custom-file-label {
    border-left: 0;
}

#app.dark .file-uploader-form {
    .custom-file-label {
        background: @color-primary;
        color: @color-secondary-text-lighter;

        &::after {
            background: @color-primary-darker;
            color: white;
        }
    }
}
</style>
