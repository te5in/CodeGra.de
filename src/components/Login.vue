<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="login">
    <b-form-fieldset>
        <input type="text"
               class="form-control"
               placeholder="Username"
               v-model="username"
               ref="username"
               @keyup.enter="submit"/>
    </b-form-fieldset>

    <b-form-fieldset>
        <password-input v-model="password"
                        placeholder="Password"
                        @keyup.native.enter="submit"/>
    </b-form-fieldset>

    <div class="text-center">
        <submit-button ref="submit"
                       @click.native="submit"
                       label="Login"
                       :show-empty="false"/>

        <div class="login-links">
            <router-link :to="{ name: 'forgot' }">
                Forgot password
            </router-link>
        </div>
    </div>
</div>
</template>

<script>
import { mapActions } from 'vuex';

import PasswordInput from './PasswordInput';
import SubmitButton from './SubmitButton';

export default {
    name: 'login',

    data() {
        return {
            username: '',
            password: '',
        };
    },

    components: {
        PasswordInput,
        SubmitButton,
    },

    mounted() {
        this.$nextTick(() => {
            if (this.$refs.username) {
                this.$refs.username.focus();
            }
        });
    },

    methods: {
        ...mapActions('user', ['login']),

        submit(event) {
            event.preventDefault();

            if (!this.password || !this.username) {
                this.$refs.submit.fail('Please enter a username and password.');
                return;
            }

            this.$refs.submit.submit(this.login({
                username: this.username,
                password: this.password,
            }).then(() => {
                this.$router.replace({ name: 'home' });
                this.$emit('login');
            }, (reason) => {
                throw reason ? reason.message : '';
            }));
        },
    },
};
</script>

<style lang="less" scoped>
@link-margin: 2em;
.login-links {
    margin-top: 1rem;

    a {
        text-decoration: underline !important;
    }
}
</style>
