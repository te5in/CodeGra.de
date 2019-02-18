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
        <submit-button tabindex="6"
                       label="Register"
                       :submit="submit"
                       @after-success="afterSubmit"
                       :confirm="PASSWORD_UNIQUE_MESSAGE"/>
            Register

            <template slot="error" slot-scope="error" v-if="error.error">
                <password-suggestions :error="error.error"/>
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

    data() {
        return {
            username: '',
            firstEmail: '',
            secondEmail: '',
            name: '',
            showHelp: false,
            firstPw: '',
            secondPw: '',
            PASSWORD_UNIQUE_MESSAGE,
        };
    },

    methods: {
        ...mapActions('user', ['updateAccessToken']),

        submit() {
            if (this.firstPw !== this.secondPw) {
                throw new Error('The two passwords do not match!');
            } else if (this.firstEmail !== this.secondEmail) {
                throw new Error('The two emails do not match!');
            }

            return this.$http.post('/api/v1/user', {
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
