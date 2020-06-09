<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="page admin">
    <local-header title="Admin"/>
    <loader v-if="loading"/>
    <div class="row" v-else>
        <div class="col-12" v-if="impersonate">
            <b-card header="Impersonate user">
                <impersonate-user />
            </b-card>
        </div>
        <div class="col-12" v-if="manage">
            <b-card header="Manage site permissions">
                <permissions-manager :showAddRole="false"
                                     fixedPermission="can_manage_site_users"
                                     :showDeleteRole="false"
                                     :getChangePermUrl="(_, roleId) => `/api/v1/roles/${roleId}`"
                                     :getRetrieveUrl="() => '/api/v1/roles/'"/>
            </b-card>
        </div>

        <div class="col-12" v-if="providers">
            <b-card header="LTI 1.3 providers">
                <lti-providers />
            </b-card>
        </div>
    </div>
</div>
</template>

<script>
import { mapGetters } from 'vuex';
import { LocalHeader, PermissionsManager, Loader, ImpersonateUser, LtiProviders } from '@/components';

import { setPageTitle } from './title';

export default {
    name: 'user-page',

    components: {
        PermissionsManager,
        Loader,
        LocalHeader,
        ImpersonateUser,
        LtiProviders,
    },

    data() {
        return {
            manage: false,
            impersonate: false,
            providers: false,
            loading: true,
        };
    },

    mounted() {
        setPageTitle('Admin page');
        // Do not forget to add new permissions to constants file
        this.$hasPermission(['can_manage_site_users', 'can_impersonate_users', 'can_manage_lti_providers']).then(
            ([manage, impersonate, providers]) => {
                this.manage = manage;
                this.impersonate = impersonate;
                this.providers = providers;
                this.loading = false;
            },
        );
    },

    computed: {
        ...mapGetters('user', ['loggedIn']),
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.row > div:not(.col-12) .card:not(:first-child) {
    margin-top: 15px;

    @media @media-no-medium {
        .card {
            margin-top: 15px;
        }
    }
}

.card {
    margin-bottom: 15px;
}

.permissions-manager {
    margin: -1.25rem;
}
</style>
