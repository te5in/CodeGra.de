<template>
<div class="home">
    <home-grid/>
</div>
</template>

<script>
import { HomeGrid } from '@/components';

import { setPageTitle } from './title';

export default {
    name: 'home-page',

    mounted() {
        setPageTitle();
    },

    components: {
        HomeGrid,
    },
};
</script>

<style lang="less" scoped>
@import "~mixins.less";

.page.home .login-wrapper {
    margin: 2em auto;
}

.logo {
    display: block;
    margin-left: auto;
    margin-right: auto;
    width: 50%;
    margin-bottom: 1em;
}
</style>
