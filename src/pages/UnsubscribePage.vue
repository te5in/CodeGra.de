<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="unsubscribe-page">
    <div class="settings-wrapper d-flex align-items-center flex-column">
        <cg-logo />
        <hr class="w-75"/>
        <notification-settings class="col-lg-6 col-md-10" :token="token" />
    </div>
</div>
</template>

<script lang="ts">
import { Vue, Component } from 'vue-property-decorator';
import NotificationSettings from '@/components/NotificationSettings';

@Component({ components: { NotificationSettings } })
export default class UnsubscribePage extends Vue {
    get token(): string {
        return this.$route.query.token ?? '';
    }
}
</script>

<style lang="less" scoped>
.settings-wrapper {
    .cg-logo {
        max-width: 25rem;
        display: block;
    }
    margin: 2rem auto;
}
</style>
