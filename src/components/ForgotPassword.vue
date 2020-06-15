<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="forgot-password">
    <b-form-fieldset>
        <input type="text"
               class="form-control"
               name="username"
               placeholder="Username"
               v-model="username"
               ref="username"
               @keyup.enter="$refs.btn.onClick"/>
    </b-form-fieldset>

    <p>
        A link to reset your password will be sent to your e-mail shortly. This
        link can be used for a limited period of time. Please check your spam
        folder if you did not receive the e-mail shortly after requesting it.
    </p>

    <b-form-fieldset class="text-center">
        <submit-button label="Request email"
                       ref="btn"
                       :submit="submit"/>

        <!-- This happens when a logged in user wants to reset its password -->
        <div class="login-links" v-if="!loggedIn">
            <router-link :to="{ name: 'login' }">
                Login
            </router-link>
        </div>
    </b-form-fieldset>
</div>
</template>

<script>
import { mapGetters } from 'vuex';

import SubmitButton from './SubmitButton';

export default {
    name: 'login',

    data() {
        return {
            username: '',
        };
    },

    components: {
        SubmitButton,
    },

    computed: {
        ...mapGetters('user', ['loggedIn']),
    },

    async mounted() {
        const userInput = await this.$waitForRef('username');
        if (userInput != null) {
            userInput.focus();
        }
    },

    methods: {
        submit() {
            if (!this.username) {
                throw new Error('Please enter a username.');
            }

            return this.$http.patch('/api/v1/login?type=reset_email', { username: this.username });
        },
    },
};
</script>

<style lang="less" scoped>
@link-margin: 2em;

.login-links {
    margin-top: 15px;
    text-align: center;

    a.login {
        text-decoration: underline !important;
    }
}
</style>
