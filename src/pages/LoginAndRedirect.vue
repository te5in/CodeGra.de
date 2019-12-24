<template>
<div class="login-and-redirect">
    <b-alert show v-if="err" variant="danger" class="m-5">
        {{ err }}
    </b-alert>
    <loader page-loader v-else/>
</div>
</template>

<script>
import Vue from 'vue';
import Toasted from 'vue-toasted';

import { mapActions } from 'vuex';
import Loader from '@/components/Loader';

Vue.use(Toasted);

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
                this.$toasted.info(
                    'You are now logged-in on CodeGrade, remember to logout after you finish your session if this is a shared system.',
                    {
                        position: 'bottom-center',
                        closeOnSwipe: false,
                        fitToScreen: true,
                        action: {
                            text: '✖',
                            onClick(_, toastObject) {
                                toastObject.goAway(0);
                            },
                        },
                    },
                );
            },
            err => {
                if (this.$utils.getProps(err, 0, 'response', 'status') === 404) {
                    this.err =
                        'The access code has expired, please click the "New Tab" button again. If this issues persists, contact support.';
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
