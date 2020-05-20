<template>
<div class="lti-providers">
    <b-modal ref="blackboardModal"
             v-if="newBlackboardProvider"
             size="lg"
             no-close-on-backdrop
             no-close-on-escape
             hide-footer
             hide-header>
        <blackboard-setup
            @done="() => blackboardModal.hide()"
            :secret="null"
            :lti-provider="newBlackboardProvider"
            admin-setup />
    </b-modal>

    <b-alert variant="danger" class="m-0" show v-if="error">
        {{ error }}
        {{ $utils.getErrorMessage(error) }}
    </b-alert>
    <div v-else-if="ltiProviders != null">
        <table class="table mb-0">
            <thead>
                <tr>
                    <th>For who</th>
                    <th>LMS</th>
                    <th>Finalized</th>
                    <th class="shrink" />
                </tr>
            </thead>
            <tbody>
                <tr v-for="ltiProvider in ltiProviders"
                    :key="ltiProvider.id">
                    <td>
                        <span v-if="ltiProvider.intended_use">{{ ltiProvider.intended_use }}</span>
                        <span v-else class="text-muted">Unknown</span>
                    </td>
                    <td>{{ ltiProvider.lms }}</td>
                    <td>{{ ltiProvider.finalized ? 'Yes' : 'No' }}</td>
                    <td class="shrink">
                        <template v-if="!ltiProvider.finalized">
                            <a href="#" class="inline-link"
                               @click.prevent="copyEditLink(ltiProvider)">
                                Copy edit link
                            </a>
                            <cg-description-popover hug-text>
                                This link can be used by anyone, even non
                                logged in users for as long as the setup is not
                                finalized. Please only distribute to one person!
                            </cg-description-popover>

                            <template v-if="ltiProvider.lms === 'Blackboard'">
                                <a href="#" class="inline-link"
                                   @click.prevent="initialSetupBlackboardProvider(ltiProvider)">
                                    Setup blackboard
                                </a>
                            </template>
                        </template>
                    </td>
                </tr>
            </tbody>
        </table>

        <div class="mt-3">
            <h6>Create a new LTI 1.3 provider</h6>
            <b-form-group label="LMS name">
                <b-form-select
                    :value="newLMSName"
                    placeholder="LMS"
                    @input="setProviderName">
                    <template v-slot:first>
                        <b-form-select-option :value="null" disabled>Please select the LMS</b-form-select-option>
                    </template>

                    <b-form-select-option v-for="opt in lmsOptions"
                                          :value="opt.value"
                                          :key="lms.value">
                        {{ lms.text }}
                    </b-form-select-option>
                </b-form-select>
            </b-form-group>

            <template v-if="newLMSName != null">
                <b-form-group>
                    <label>
                        For which institution is this connection?
                        <cg-description-popover hug-text>
                            This value is not used internally by CodeGrade, it
                            is just for easier accounting of all providers.
                        </cg-description-popover>
                    </label>
                    <input class="form-control"
                           placeholder="e.g. Universiteit van Amsterdam"
                           v-model="newForWho"/>
                </b-form-group>

                <b-form-group>
                    <label>
                        The ISS of the new integration
                    </label>
                    <input class="form-control"
                           v-model="newIss"
                           :disabled="issDisabled"
                           :placeholder="issPlaceholder"/>
                </b-form-group>

                <cg-submit-button :submit="submitNewProvider"
                                  @after-success="afterSubmitNewProvider"
                                  class="float-right"
                                  confirm="Are you sure you want to create a new LTI Provider?"
                                  confirm-in-modal />
            </template>
        </div>

    </div>
    <div v-else>
        <cg-loader />
    </div>
</div>
</template>

<script lang="ts">
    import { Vue, Component, Ref } from 'vue-property-decorator';
import { LTI1p3ProviderNames, LTI1p3ProviderName } from '@/lti_providers';
import { BModal } from 'bootstrap-vue';

import * as api from '@/api/v1';

import BlackboardSetup from './LtiProviderSetup/BlackboardSetup';

@Component({ components: { BlackboardSetup } })
export default class LtiProviders extends Vue {
    error: Error | null = null;

    ltiProviders: api.lti.LTI1p3ProviderServerData[] | null = null;

    newLMSName: LTI1p3ProviderName | null = null;

    newIss: string | null = null;

    newForWho: string = '';

    newBlackboardProvider: api.lti.LTI1p3ProviderServerData | null = null;

    @Ref() readonly blackboardModal!: BModal;

    mounted() {
        this.load();
    }

    async load() {
        this.ltiProviders = null;
        this.error = null;

        try {
            this.ltiProviders = (await api.lti.getAllLti1p3Provider()).data;
        } catch (e) {
            this.error = e;
        }
    }

    // eslint-disable-next-line class-methods-use-this
    get lmsOptions() {
        return LTI1p3ProviderNames.map(cur => ({ value: cur, text: cur }));
    }

    get issDisabled(): boolean {
        switch (this.newLMSName) {
            case 'Brightspace':
            case 'Moodle':
            case null:
                return false;
            case 'Blackboard':
            case 'Canvas':
                return true;
            default:
                return this.$utils.AssertionError.assertNever(this.newLMSName);
        }
    }

    get issPlaceholder(): string {
        switch (this.newLMSName) {
            case 'Brightspace':
            case 'Moodle':
            case 'Blackboard':
                return 'The ISS for the new provider, this is the url on which the LMS is hosted.';
            case null:
            case 'Canvas':
                return '';
            default:
                return this.$utils.AssertionError.assertNever(this.newLMSName);
        }
    }

    setProviderName(name: LTI1p3ProviderName | null): void {
        this.newLMSName = name;

        switch (name) {
            case 'Canvas':
                this.newIss = 'https://canvas.instructure.com';
                break;
            case 'Blackboard':
                this.newIss = 'https://blackboard.com';
                break;
            case null:
            case 'Moodle':
            case 'Brightspace':
                this.newIss = null;
                break;
            default:
                this.$utils.AssertionError.assertNever(name);
        }
    }

    submitNewProvider() {
        // This can never happen because of the template structure.
        this.$utils.AssertionError.assert(this.newLMSName != null);

        if (!this.newIss || !this.newForWho) {
            throw new Error('Please make sure that no fields are empty.');
        }

        return this.$http.post('/api/v1/lti1.3/providers/', {
            iss: this.newIss,
            lms: this.newLMSName,
            intended_use: this.newForWho,
        });
    }

    async afterSubmitNewProvider({ data }: { data: api.lti.NonFinalizedLTI1p3ProviderServerData }) {
        this.newIss = null;
        this.newLMSName = null;
        this.newForWho = '';
        if (this.ltiProviders == null) {
            await this.load();
        } else {
            this.ltiProviders.push(data);
        }

        if (data.lms === 'Blackboard') {
            this.initialSetupBlackboardProvider(data);
        }
    }

    async initialSetupBlackboardProvider(prov: api.lti.NonFinalizedLTI1p3ProviderServerData) {
        this.newBlackboardProvider = prov;
        await this.$nextTick();
        this.blackboardModal.show();
    }

    copyEditLink(ltiProvider: api.lti.LTI1p3ProviderServerData) {
        this.$utils.AssertionError.assert(!ltiProvider.finalized);

        this.$copyText(this.$utils.buildUrl(
            ['lti_providers', ltiProvider.id, 'setup'],
            {
                baseUrl: this.$userConfig.externalUrl,
                query: {
                    secret: ltiProvider.edit_secret ?? '',
                },
            },
        ));
    }
}
</script>
