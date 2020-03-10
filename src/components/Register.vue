<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="register">
    <b-form-fieldset>
        <b-input-group :prepend="fieldLabels.username">
            <input type="text"
                   class="form-control"
                   v-model="username"
                   tabindex="1"
                   ref="username"/>
            <b-input-group-append is-text>
                <description-popover
                    placement="top"
                    description="You cannot change this after registration!" />
            </b-input-group-append>
        </b-input-group>
    </b-form-fieldset>

    <b-form-fieldset>
        <b-input-group :prepend="fieldLabels.name">
            <input type="text"
                   class="form-control"
                   v-model="name"
                   tabindex="2"
                   ref="name"/>
        </b-input-group>
    </b-form-fieldset>

    <b-form-fieldset>
        <b-input-group :prepend="fieldLabels.firstEmail">
            <input type="email"
                   class="form-control"
                   v-model="firstEmail"
                   tabindex="2"
                   ref="email"/>
        </b-input-group>
    </b-form-fieldset>

    <b-form-fieldset>
        <b-input-group :prepend="fieldLabels.secondEmail">
            <input type="email"
                   class="form-control"
                   v-model="secondEmail"
                   tabindex="3"
                   ref="email"/>
        </b-input-group>
    </b-form-fieldset>

    <password-input v-model="firstPw"
                    :label="fieldLabels.firstPw"
                    name="password"
                    tabindex="4"/>
    <password-input v-model="secondPw"
                    :label="fieldLabels.secondPw"
                    name="repeat-password"
                    tabindex="5"/>

    <div class="text-center">
        <submit-button tabindex="6"
                       label="Register"
                       :submit="submit"
                       @after-success="afterSubmit"
                       :confirm="PASSWORD_UNIQUE_MESSAGE">
            <template slot="error"
                      slot-scope="error"
                      v-if="error.error">
                <password-suggestions
                    v-if="$utils.getProps(error.error, null, 'response', 'data', 'feedback')"
                    :error="error.error"/>

                <template v-else>
                    <p class="mb-0">{{ $utils.getErrorMessage(error.error) }}</p>

                    <ul v-if="$utils.getProps(error.error, 0, 'messages', 'length') > 0"
                        class="mb-0 pl-3 text-left">
                        <li v-for="msg in error.error.messages">
                            {{ msg }}
                        </li>
                    </ul>
                </template>
            </template>
        </submit-button>
    </div>
</div>
</template>

<script>
import { mapActions } from 'vuex';

import { PASSWORD_UNIQUE_MESSAGE } from '@/constants';

import SubmitButton from './SubmitButton';
import DescriptionPopover from './DescriptionPopover';
import PasswordInput from './PasswordInput';
import PasswordSuggestions from './PasswordSuggestions';

export default {
    name: 'register',

    props: {
        registrationUrl: {
            type: String,
            required: true,
        },
    },

    data() {
        return {
            username: '',
            firstEmail: '',
            secondEmail: '',
            name: '',
            firstPw: '',
            secondPw: '',

            fieldLabels: {
                username: 'Username',
                name: 'Full name',
                firstEmail: 'Email',
                secondEmail: 'Repeat email',
                firstPw: 'Password',
                secondPw: 'Repeat password',
            },

            PASSWORD_UNIQUE_MESSAGE,
        };
    },

    methods: {
        ...mapActions('user', ['updateAccessToken']),

        submit() {
            const errors = [];

            Object.entries(this.fieldLabels).forEach(([key, label]) => {
                if (this[key].length === 0) {
                    errors.push(`Field "${label}" is empty.`);
                }
            });

            if (this.firstPw !== this.secondPw) {
                errors.push('The passwords do not match.');
            }

            if (this.firstEmail !== this.secondEmail) {
                errors.push('The emails do not match.');
            }

            if (errors.length > 0) {
                const err = new Error();
                err.messages = errors;
                throw err;
            }

            return this.$http.post(this.registrationUrl, {
                username: this.username,
                password: this.firstPw,
                email: this.firstEmail,
                name: this.name,
            });
        },

        afterSubmit(response) {
            const token = response.data.access_token;
            if (token) {
                this.updateAccessToken(token).then(() => {
                    this.$router.push({
                        name: 'home',
                        query: { sbloc: 'm' },
                    });
                });
            }
        },
    },

    components: {
        SubmitButton,
        DescriptionPopover,
        PasswordInput,
        PasswordSuggestions,
    },
};
</script>
