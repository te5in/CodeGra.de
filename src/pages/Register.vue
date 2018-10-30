<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="register">
    <div class="register-wrapper">
        <img class="logo" src="static/img/codegrade.svg" v-if="darkMode"/>
        <img class="logo" src="static/img/codegrade-inv.svg" v-else/>
        <register class="register"/>
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
@import "~mixins.less";

.page.register .register-wrapper {
    margin: 2em auto;

    .register {
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
