<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<b-form-fieldset class="password-input">
    <b-input-group>
        <slot name="prepend">
            <b-input-group-prepend is-text v-if="label">{{ label }}</b-input-group-prepend>
        </slot>
        <input :tabindex="tabindex"
               type="password"
               v-model="password"
               :name="name"
               class="form-control"
               :placeholder="placeholder"/>
    </b-input-group>
</b-form-fieldset>
</template>

<script>
export default {
    name: 'password-input',

    props: {
        value: {
            default: '',
        },

        name: {
            required: true,
            type: String,
        },

        label: {
            default: '',
            type: String,
        },

        placeholder: {
            default: '',
            type: String,
        },

        tabindex: {
            default: undefined,
        },
    },

    data() {
        return {
            visible: false,
            password: this.value,
        };
    },

    watch: {
        value(val) {
            this.password = val;
        },

        password() {
            this.$emit('input', this.password);
        },
    },
};
</script>
