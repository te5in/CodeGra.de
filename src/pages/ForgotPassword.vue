<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="forgot-password">
    <div class="forgot-password-wrapper">
        <img class="standalone-logo" src="static/img/codegrade.svg" v-if="darkMode"/>
        <img class="standalone-logo" src="static/img/codegrade-inv.svg" v-else/>
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
        margin: 0 auto;
        max-width: 25rem;
        text-align: justify;
    }
}
</style>
