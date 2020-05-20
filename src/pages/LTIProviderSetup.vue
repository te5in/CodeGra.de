<template>
<div class="lti-provider-setup">
    <b-alert v-if="error"
             variant="danger"
             show>
        {{ $utils.getErrorMessage(error) }}
    </b-alert>
    <lti-provider-setup v-else-if="ltiProvider"
                        @update-provider="ltiProvider = $event"
                        :secret="setupSecret"
                        :lti-provider="ltiProvider" />
    <cg-loader page-loader v-else />
</div>
</template>

<script lang="ts">
import { Vue, Component, Watch } from 'vue-property-decorator';

import LtiProviderSetup from '@/components/LtiProviderSetup';

import * as api from '@/api/v1';

@Component({ components: { LtiProviderSetup } })
export default class LTIProviderSetup extends Vue {
    error: Error | null = null;

    get ltiProviderId(): string {
        return this.$route.params.ltiProviderId;
    }

    get setupSecret(): string | null {
        return this.$route.query.setupSecret ?? null;
    }

    ltiProvider: api.lti.LTI1p3ProviderServerData | null = null;

    @Watch('ltiProviderId', { immediate: true })
    onLtiProviderIdChange() {
        this.load();
    }

    async load() {
        this.ltiProvider = null;
        try {
            this.ltiProvider = (await api.lti.getLti1p3Provider(
                this.ltiProviderId,
                this.setupSecret,
            )).data;
        } catch (e) {
            this.error = e;
        }
    }
}
</script>
