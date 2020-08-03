<template>
<div class="sso-login">
    <local-header show-logo>
        Finalizing login&hellip;
    </local-header>

    <b-alert v-if="error != null" variant="danger" show>
        {{ $utils.getErrorMessage(error) }}
    </b-alert>
    <cg-loader v-else page-loader />
</div>
</template>

<script lang="ts">
    import { Vue, Watch, Component } from 'vue-property-decorator';

import { mapActions } from 'vuex';

// @ts-ignore
import LocalHeader from '@/components/LocalHeader';
@Component({
    components: { LocalHeader },
    methods: {
        ...mapActions('user', ['updateAccessToken']),
    },
})
export default class SsoLogin extends Vue {
    error: Error | null = null;

    private updateAccessToken!: (newToken: string) => Promise<unknown>;

    get blobId() {
        return this.$route.params.blobId;
    }

    get next() {
        return this.$route.query.next;
    }

    @Watch('blobId', { immediate: true })
    async loadData() {
        this.error = null;
        try {
            const response = await this.$http.post(`/api/sso/saml2/jwts/${this.blobId}`);
            await this.updateAccessToken(response.data.access_token);
            this.$router.replace(this.next ?? '/');
        } catch (error) {
            this.error = error;
        }
    }
}
</script>
