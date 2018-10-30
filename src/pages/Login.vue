<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="login">
    <div class="login-wrapper">
        <img class="logo" src="static/img/codegrade.svg" v-if="darkMode"/>
        <img class="logo" src="static/img/codegrade-inv.svg" v-else/>
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
@import "~mixins.less";

.login-wrapper {
    margin: 2em auto;

    .login {
        @media @media-medium {
            max-width: 768px;
            margin: 0 auto;
        }
    }
}

.logo {
    display: block;
    margin-left: auto;
    margin-right: auto;
    width: 50%;
    margin-bottom: 1em;
}
</style>
