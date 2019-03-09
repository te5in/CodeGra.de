<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="login">
    <div class="login-wrapper">
        <img class="standalone-logo" src="static/img/codegrade.svg" v-if="darkMode"/>
        <img class="standalone-logo" src="static/img/codegrade-inv.svg" v-else/>
        <login class="login"/>
    </div>
</div>
</template>

<script>
import { mapGetters } from 'vuex';

import { Login } from '@/components';

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
