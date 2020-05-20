/* SPDX-License-Identifier: AGPL-3.0-only */
import axios, { AxiosResponse } from 'axios';
import { buildUrl } from '@/utils';
import { LTI1p3Capabilities } from '@/lti_providers';

/* eslint-disable camelcase */
type BaseLTI1p3ProviderServerData = {
    id: string;
    lms: string;
    intended_use: string;
    capabilities: LTI1p3Capabilities;
};

export type NonFinalizedLTI1p3ProviderServerData = BaseLTI1p3ProviderServerData & {
    finalized: false;
    iss: string | null;
    auth_login_url: string | null;
    auth_token_url: string | null;
    client_id: string | null;
    key_set_url: string | null;
    custom_fields: Record<string, string>;
    public_jwk: Record<string, string>;
    edit_key: string | null;
    edit_secret: string | null;
    public_key: string;
};

type FinalizedLTI1p3ProviderServerData = BaseLTI1p3ProviderServerData & {
    finalized: true;
    edit_secret: null;
};
/* eslint-enable camelcase */

export type LTI1p3ProviderServerData =
    | FinalizedLTI1p3ProviderServerData
    | NonFinalizedLTI1p3ProviderServerData;

export function getLti1p3Provider(
    ltiProviderId: string,
    secret: string | null,
): Promise<AxiosResponse<LTI1p3ProviderServerData>> {
    const query: Record<string, string> = {};
    if (secret != null) {
        query.secret = secret;
    }

    return axios.get(buildUrl(['api', 'v1', 'lti1.3', 'providers', ltiProviderId], { query }));
}

export function getAllLti1p3Provider(): Promise<AxiosResponse<LTI1p3ProviderServerData[]>> {
    return axios.get('/api/v1/lti1.3/providers/');
}

export function updateLti1p3Provider(
    ltiProvider: NonFinalizedLTI1p3ProviderServerData,
    secret: string | null,
    updatedData: {
        /* eslint-disable camelcase */
        client_id?: string;
        auth_token_url?: string;
        auth_login_url?: string;
        key_set_url?: string;
        finalize?: boolean;
        /* eslint-enable camelcase */
    },
): Promise<AxiosResponse<LTI1p3ProviderServerData>> {
    const query: Record<string, string> = {};
    if (secret != null) {
        query.secret = secret;
    }

    return axios.patch(
        buildUrl(['api', 'v1', 'lti1.3', 'providers', ltiProvider.id], { query }),
        updatedData,
    );
}
