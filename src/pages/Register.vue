<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="register">
    <div class="register-wrapper">
        <img class="standalone-logo" src="/static/img/codegrade.svg" v-if="darkMode"/>
        <img class="standalone-logo" src="/static/img/codegrade-inv.svg" v-else/>
        <h4>
            Register
            <span v-if="$route.query.register_for">
                for {{ $route.query.register_for }}
            </span>
        </h4>
        <register class="register"
                  :registration-url="registrationUrl" />
    </div>
</div>
</template>

<script>
import { mapGetters } from 'vuex';

import { Register } from '@/components';

import { setPageTitle } from './title';

export default {
    name: 'register-page',

    computed: {
        ...mapGetters('pref', ['darkMode']),

        registrationUrl() {
            const courseId = this.$route.query.course_id;
            const linkId = this.$route.query.course_register_link_id;
            if (courseId == null || linkId == null) {
                return '/api/v1/user';
            }
            return `/api/v1/courses/${courseId}/registration_links/${linkId}/user`;
        },
    },

    mounted() {
        setPageTitle('Register');
    },

    components: {
        Register,
    },
};
</script>

<style lang="less" scoped>
h4 {
    margin-bottom: 1rem;
    font-weight: normal;
    text-align: center;
}

.page.register .register-wrapper {
    margin: 0 auto;
    max-width: 25rem;
}
</style>
