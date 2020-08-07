<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="login">
    <b-form-group label="Username:">
        <input type="text"
               class="form-control"
               placeholder="Enter your username"
               v-model="username"
               ref="username"
               name="username"
               @keyup.enter="$refs.submit.onClick"/>
    </b-form-group>

    <b-form-group label="Password:">
        <password-input v-model="password"
                        placeholder="Enter your password"
                        name="password"
                        @keyup.native.enter="$refs.submit.onClick"/>
    </b-form-group>

    <div class="text-right">
        <submit-button :label="loginLabel"
                       ref="submit"
                       :submit="submit"
                       @success="success"
                       :wait-at-least="0">
            <template slot="warning" slot-scope="scope">
                {{ scope.warning.messages.map(x => x.text).join(' ') }}<br>
                Close this message to continue.
            </template>
        </submit-button>

        <div class="login-links" v-if="!hideForget">
            <router-link :to="{ name: 'forgot' }">
                Forgot password
            </router-link>
        </div>
    </div>

    <sso-providers @saml-login="$emit('saml-login', $event)"
                   allow-login>
        <hr />
        <h5>Or login using</h5>
    </sso-providers>
</div>
</template>

<script>
import { mapActions } from 'vuex';

import PasswordInput from './PasswordInput';
import SubmitButton from './SubmitButton';
import SsoProviders from './SsoProviders';

export default {
    name: 'login',

    props: {
        hideForget: {
            type: Boolean,
            default: false,
        },

        loginLabel: {
            type: String,
            default: 'Login',
        },
    },

    data() {
        return {
            username: '',
            password: '',
        };
    },

    components: {
        PasswordInput,
        SubmitButton,
        SsoProviders,
    },

    mounted() {
        this.$waitForRef('username').then(userInput => {
            if (userInput != null) {
                this.$refs.username.focus();
            }
        });
    },

    methods: {
        ...mapActions('user', ['login']),

        submit() {
            if (!this.password || !this.username) {
                return Promise.reject(new Error('Please enter a username and password.'));
            }

            return this.$http.post('/api/v1/login?with_permissions', {
                username: this.username,
                password: this.password,
            });
        },

        success(response) {
            this.login(response).then(() => {
                this.$emit('login');
            });
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
