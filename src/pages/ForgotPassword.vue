<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="forgot-password">
    <div class="forgot-password-wrapper">
        <img class="logo" src="static/img/codegrade.svg" v-if="darkMode"/>
        <img class="logo" src="static/img/codegrade-inv.svg" v-else/>
    <forgot-password class="forgot-password"/>
</div>
</div>
</template>

<script>
import { mapGetters } from 'vuex';

import { ForgotPassword } from '@/components';

import { setPageTitle } from './title';

export default {
    name: 'forgot-password-page',

    computed: {
        ...mapGetters('pref', ['darkMode']),
    },

    mounted() {
        setPageTitle('Forgot password');
    },

    components: {
        ForgotPassword,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.forgot-password-wrapper {
    margin: 2em auto;

    .forgot-password {
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
