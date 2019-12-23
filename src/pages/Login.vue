<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="login">
    <div class="login-wrapper">
        <cg-logo :inverted="!darkMode"
                 class="standalone-logo" />
        <login class="login"/>
    </div>
</div>
</template>

<script>
import { mapGetters } from 'vuex';

import { Login, CgLogo } from '@/components';

import { setPageTitle } from './title';

export default {
    name: 'login-page',

    computed: {
        ...mapGetters('pref', ['darkMode']),
    },

    mounted() {
        setPageTitle('Login');
    },

    components: {
        Login,
        CgLogo,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.login-wrapper {
    margin: 2em auto;

    .login {
        max-width: 25rem;
        margin: 0 auto;
    }
}
</style>
