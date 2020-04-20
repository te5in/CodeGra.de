<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="login-and-redirect">
    <b-alert show v-if="err" variant="danger" class="m-5">
        {{ err }}
    </b-alert>
    <loader page-loader v-else/>
</div>
</template>

<script>
import { mapActions } from 'vuex';
import Loader from '@/components/Loader';

export default {
    name: 'login-and-redirect',

    computed: {
        loginFile() {
            return this.$route.params.loginFile;
        },

        nextRoute() {
            if (this.$route.query.next) {
                return JSON.parse(this.$route.query.next);
            }
            return { name: 'home' };
        },
    },

    data() {
        return {
            err: null,
        };
    },

    methods: {
        ...mapActions('user', ['updateAccessToken']),
    },

    mounted() {
        this.$http.get(`/api/v1/files/${this.loginFile}`).then(
            async ({ data }) => {
                await this.updateAccessToken(data);
                this.$router.replace(this.nextRoute);
                // The toast must be emitted on root because this component
                // will no longer exist when it is shown.
                this.$root.$bvToast.toast(
                    `You are now logged-in on CodeGrade, remember to logout
                    after you finish your session if this is a shared system.`,
                    {
                        title: 'CodeGrade',
                        toaster: 'b-toaster-bottom-center',
                        variant: 'info',
                    },
                );
            },
            err => {
                if (this.$utils.getProps(err, 0, 'response', 'status') === 404) {
                    this.err = `The access code has expired, please click the
                        "New Tab" button again. If this issues persists,
                        contact support.`;
                } else {
                    this.err = this.$utils.getErrorMessage(err);
                }
            },
        );
    },

    components: {
        Loader,
    },
};
</script>
