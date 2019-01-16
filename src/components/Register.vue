<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="register">
    <b-form-fieldset>
        <b-input-group prepend="Your username">
            <input type="text"
                   class="form-control"
                   v-model="username"
                   tabindex="1"
                   ref="username"/>
            <b-input-group-append is-text>
                <description-popover
                    description="You cannot change this after registration!"
                    :show="showHelp"/>
            </b-input-group-append>
        </b-input-group>
    </b-form-fieldset>

    <b-form-fieldset>
        <b-input-group prepend="Your full name">
            <input type="text"
                   class="form-control"
                   v-model="name"
                   tabindex="2"
                   ref="name"/>
        </b-input-group>
    </b-form-fieldset>

    <b-form-fieldset>
        <b-input-group prepend="Your email">
            <input type="email"
                   class="form-control"
                   v-model="firstEmail"
                   tabindex="2"
                   ref="email"/>
        </b-input-group>
    </b-form-fieldset>

    <b-form-fieldset>
        <b-input-group prepend="Repeat email">
            <input type="email"
                   class="form-control"
                   v-model="secondEmail"
                   tabindex="3"
                   ref="email"/>
        </b-input-group>
    </b-form-fieldset>

    <password-input v-model="firstPw"
                    label="Password"
                    tabindex="4"/>
    <password-input v-model="secondPw"
                    label="Repeat password"
                    tabindex="5"/>

    <div class="text-center">
        <submit-button label="Register"
                       @click="submit"
                       :delay="5000"
                       tabindex="6"
                       ref="submit"
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
    </div>
</div>
</template>

<script>
import { mapActions } from 'vuex';

import SubmitButton from './SubmitButton';
import DescriptionPopover from './DescriptionPopover';
import PasswordInput from './PasswordInput';

export default {
    name: 'register',

    data() {
        return {
            username: '',
            firstEmail: '',
            secondEmail: '',
            name: '',
            showHelp: false,
            firstPw: '',
            secondPw: '',
        };
    },

    methods: {
        ...mapActions('user', ['updateAccessToken']),

        submit() {
            const button = this.$refs.submit;

            if (this.firstPw !== this.secondPw) {
                return button.fail('The two passwords do not match!');
            } else if (this.firstEmail !== this.secondEmail) {
                return button.fail('The two emails do not match!');
            }

            return button.submitFunction(() =>
                this.$http
                    .post('/api/v1/user', {
                        username: this.username,
                        password: this.firstPw,
                        email: this.firstEmail,
                        name: this.name,
                    })
                    .then(
                        async ({ data }) => {
                            if (data.access_token) {
                                await this.updateAccessToken(data.access_token);
                                this.$router.push({
                                    name: 'me',
                                    query: { sbloc: 'm' },
                                });
                            }
                        },
                        ({ response }) => {
                            throw response.data.feedback || {
                                warning: response.data.message,
                            };
                        },
                    ),
            );
        },
    },

    components: {
        SubmitButton,
        DescriptionPopover,
        PasswordInput,
    },
};
</script>

<style lang="less" scoped>
.error-message {
    text-align: left;

    ul {
        margin-bottom: 0;
        padding-left: 1rem;
    }
}
</style>
