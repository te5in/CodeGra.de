<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="forgot-password">
    <div class="forgot-password-wrapper">
        <cg-logo :inverted="!darkMode"
                 class="standalone-logo" />
        <forgot-password class="forgot-password"/>
    </div>
</div>
</template>

<script>
import { mapGetters } from 'vuex';

import { CgLogo, ForgotPassword } from '@/components';

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
        CgLogo,
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
