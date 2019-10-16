<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="impersonate-user">
    <b-form-fieldset>
        <user-selector v-model="otherUser"
                       :use-selector="canListUsers"
                       placeholder="User to impersonate"/>
    </b-form-fieldset>
    <b-form-fieldset>
        <input type="password"
               v-model="password"
               placeholder="Own password"
               @keydown.ctrl.enter="$refs.submitBtn.onClick()"
               class="form-control"/>
    </b-form-fieldset>
    <div class="text-right">
        <submit-button :submit="impersonate" @after-success="afterImpersonate"
                       ref="submitBtn"/>
    </div>
</div>
</template>

<script>
import { mapActions } from 'vuex';

import SubmitButton from './SubmitButton';
import UserSelector from './UserSelector';

export default {
    name: 'impersonate-user',

    data() {
        return {
            password: '',
            otherUser: '',
            canListUsers: false,
        };
    },

    async mounted() {
        this.canListUsers = await this.$hasPermission('can_search_users');
    },

    methods: {
        ...mapActions('user', ['login', 'logout']),

        impersonate() {
            return this.$http.post('/api/v1/login?impersonate', {
                own_password: this.password,
                username: this.otherUser.username,
            });
        },

        afterImpersonate(data) {
            this.logout().then(async () => {
                await this.login(data);
                this.$router.replace({ name: 'home' });
            });
        },
    },

    components: {
        SubmitButton,
        UserSelector,
    },
};
</script>
