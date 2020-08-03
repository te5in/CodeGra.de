<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="sso-providers">
    <b-alert variant="danger" class="m-0" show v-if="error">
        {{ error }}
        {{ $utils.getErrorMessage(error) }}
    </b-alert>
    <div v-else-if="providers != null">
        <slot  />

        <ul class="mb-0 list-group">
            <li v-for="provider in providers" :key="provider.id"
                :class="{ 'clickable': !adminMode }"
                class="list-group-item sso-provider-list-item">
                <a :href="adminMode ? undefined : provider.loginUrl"
                   @click.prevent="() => !adminMode && $emit('saml-login', provider)">
                    <div class="d-flex flex-row">
                        <img :src="provider.logo.url"
                             v-if="provider.logo"
                             class="d-block pr-3"
                             :style="`max-width: ${minWidth / 2}px;`"
                             height="auto"
                             width="auto" />
                        <div>
                            <h4>{{ provider.name }}</h4>

                            <p v-if="provider.description">
                                {{ provider.description }}
                            </p>

                            <p v-if="adminMode">
                                <b>SP metadata URL:</b>
                                <a :href="provider.metadatUrl" v-if="adminMode">
                                    {{ provider.metadataUrl }}
                                </a>
                            </p>
                        </div>
                    </div>
                </a>
            </li>
        </ul>
        <div v-if="adminMode">
            <hr />
            <h6>Create a new SSO Identity Provider</h6>
            <b-form>
                <b-form-group label="Metadata URL:">
                    <input type="text"
                           class="form-control"
                           placeholder="Enter metadata url"
                           v-model="newProviderMetadataUrl"
                           @keyup.enter="() => $refs.create.onClick()"/>
                </b-form-group>

                <b-form-group label="Backup name:"
                              description="If no name can be found in the metadata of SSO IDP this will be displayed to the user.">
                    <input type="text"
                           class="form-control"
                           placeholder="Enter name"
                           v-model="newProviderMetadataName"
                           @keyup.enter="() => $refs.create.onClick()"/>
                </b-form-group>

                <div class="text-right">
                    <cg-submit-button
                        ref="create"
                        :submit="createNew"
                        @after-success="afterCreate" />
                </div>
            </b-form>
        </div>
    </div>
    <cg-loader v-else-if="adminMode" />
    <div
</div>
</template>

<script lang="ts">
import { Vue, Component, Prop } from 'vue-property-decorator';
import { AxiosResponse } from 'axios';

import * as api from '@/api/v1';
import * as models from '@/models';

@Component
export default class SSOProviders extends Vue {
    providers: null | models.SSOProvider[] = null;

    error: Error | null = null;

    @Prop({ default: false })
    adminMode!: boolean;

    private newProviderMetadataUrl: string = '';

    private newProviderMetadataName: string = '';

    mounted() {
        this.loadData();
    }

    async loadData() {
        this.providers = null;
        this.error = null;

        try {
            this.providers = await api.ssoProviders.get();
        } catch (e) {
            this.error = e;
        }
    }

    createNew() {
        return this.$http.post('/api/v1/sso_providers/', {
            metadata_url: this.newProviderMetadataUrl,
            name: this.newProviderMetadataName,
        });
    }

    afterCreate(response: AxiosResponse<models.Saml2ProviderServerData>) {
        if (this.providers == null) {
            this.providers = [];
        }
        this.providers.push(models.makeSSOProvider(response.data));
    }

    get minWidth(): number {
        if (this.providers == null || this.providers.length === 0) {
            return 0;
        }

        let min = Infinity;
        this.providers.forEach(prov => {
            if (prov.logo == null) {
                return;
            }
            min = Math.min(min, prov.logo.width);
        });
        return min === Infinity ? 0 : min;
    }
}
</script>

<style lang="less">
@import '~mixins.less';

.sso-providers .sso-provider-list-item {
    &.clickable:hover {
        background-color: rgba(0, 0, 0, 0.075);
        cursor: pointer;
    }
    img {
        margin: auto 1rem;
        object-fit: scale-down;
    }
}
</style>
