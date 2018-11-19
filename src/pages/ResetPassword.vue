<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="reset-password row justify-content-center">
    <b-form-fieldset class="col-sm-8 text-center"
                     @keyup.native.ctrl.enter="submit">
        <h4>Reset your password</h4>

        <password-input label="New password"
                        v-model="newPw"/>
        <password-input label="Confirm password"
                        v-model="confirmPw"/>

        <submit-button ref="btn"
                       @click="submit"
                       popover-placement="bottom"
                       :delay="5000"
                       confirm="Please make sure you use a unique password, and at least different
                                from the password you use for your LMS.">
            <template slot="error" slot-scope="error">
                <div class="error-message">
                    <span>{{ error.messages.warning }}</span>

                    <span v-if="error.messages.suggestions">
                        <div style="margin-top: 1rem;"><b>Suggestions:</b></div>
                        <ul>
                            <li v-for="message in error.messages.suggestions">
                                {{ message }}
                            </li>
                        </ul>
                    </span>
                </div>
            </template>
        </submit-button>
    </b-form-fieldset>
</div>
</template>

<script>
import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/eye';
import 'vue-awesome/icons/eye-slash';
import { mapActions } from 'vuex';

import { SubmitButton, PasswordInput } from '@/components';

export default {
    name: 'reset-password',

    data() {
        return {
            newPw: '',
            confirmPw: '',
        };
    },

    components: {
        Icon,
        SubmitButton,
        PasswordInput,
    },

    methods: {
        ...mapActions('user', [
            'updateAccessToken',
        ]),

        submit() {
            const button = this.$refs.btn;

            if (this.newPw !== this.confirmPw) {
                return button.fail('The passwords don\'t match');
            } else if (this.newPw === '') {
                return button.fail('The new password may not be empty');
            }

            return button.submitFunction(() =>
                this.$http.patch('/api/v1/login?type=reset_password', {
                    user_id: Number(this.$route.query.user),
                    token: this.$route.query.token,
                    new_password: this.newPw,
                }).then(async ({ data }) => {
                    await this.updateAccessToken(data.access_token);
                    this.$router.replace({
                        name: 'home',
                        query: { sbloc: 'm' },
                    });
                }, ({ response }) => {
                    throw response.data.feedback || { warning: response.data.message };
                }));
        },
    },
};
</script>

<style lang="less" scoped>
.reset-password {
    margin-top: 1rem;
}

h4 {
    margin-bottom: 1rem;
}

.error-message {
    text-align: left;

    ul {
        margin-bottom: 0;
        padding-left: 1rem;
    }
}
</style>
