<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="reset-password justify-content-center">
    <cg-logo :inverted="!darkMode"
             class="standalone-logo" />

    <b-form-fieldset class="col-sm-8 text-center form-wrapper"
                     @keyup.native.ctrl.enter="$refs.btn.onClick">
        <h4>Reset your password</h4>

        <password-input label="New password"
                        name="new-password"
                        v-model="newPw"/>
        <password-input label="Confirm password"
                        name="confirm-password"
                        v-model="confirmPw"/>

        <submit-button ref="btn"
                       :submit="submit"
                       @after-success="afterSubmit"
                       popover-placement="bottom"
                       :confirm="PASSWORD_UNIQUE_MESSAGE">
            <template slot="error" slot-scope="error" v-if="error.error">
                <password-suggestions :error="error.error"/>
            </template>
        </submit-button>
    </b-form-fieldset>
</div>
</template>

<script>
import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/eye';
import 'vue-awesome/icons/eye-slash';
import { mapActions, mapGetters } from 'vuex';

import { PASSWORD_UNIQUE_MESSAGE } from '@/constants';

import { CgLogo, SubmitButton, PasswordInput, PasswordSuggestions } from '@/components';

export default {
    name: 'reset-password',

    data() {
        return {
            newPw: '',
            confirmPw: '',
            PASSWORD_UNIQUE_MESSAGE,
        };
    },

    components: {
        Icon,
        CgLogo,
        SubmitButton,
        PasswordInput,
        PasswordSuggestions,
    },

    computed: {
        ...mapGetters('pref', ['darkMode']),
    },

    methods: {
        ...mapActions('user', ['updateAccessToken']),

        submit() {
            if (this.newPw !== this.confirmPw) {
                throw new Error("The passwords don't match");
            } else if (this.newPw === '') {
                throw new Error('The new password may not be empty');
            }

            return this.$http.patch('/api/v1/login?type=reset_password', {
                user_id: Number(this.$route.query.user),
                token: this.$route.query.token,
                new_password: this.newPw,
            });
        },

        async afterSubmit({ data }) {
            await this.updateAccessToken(data.access_token);

            this.$router.replace({
                name: 'home',
                query: { sblock: 'm' },
            });
        },
    },
};
</script>

<style lang="less" scoped>
h4 {
    margin-bottom: 1rem;
    font-weight: normal;
}

.form-wrapper {
    margin: 0 auto;
    max-width: 25rem;
    padding: 0;
}
</style>
