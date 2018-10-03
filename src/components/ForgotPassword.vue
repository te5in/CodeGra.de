<template>
<div class="forgot-password">
    <b-form-fieldset>
        <input type="text"
                class="form-control"
                placeholder="Username"
                v-model="username"
                ref="username"
                @keyup.enter="submit"/>
    </b-form-fieldset>

    <p>
        A link to reset your password will be sent to your e-mail shortly. This
        link can be used for a limited period of time. Please check your spam
        folder if you did not receive the e-mail shortly after requesting it.
    </p>

    <b-form-fieldset class="text-center">
        <submit-button ref="submit"
                    @click="submit"
                    label="Request email"
                    :show-empty="false"/>

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

    mounted() {
        this.$nextTick(() => {
            if (this.$refs.username) {
                this.$refs.username.focus();
            }
        });
    },

    methods: {
        submit(event) {
            event.preventDefault();

            if (!this.username) {
                this.$refs.submit.fail('Please enter a username.');
                return;
            }

            this.$refs.submit.submit(this.$http.patch('/api/v1/login?type=reset_email', {
                username: this.username,
            }).catch((err) => {
                throw err.response.data.message;
            }));
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
