<template>
<div class="assignment-login">
    <local-header show-logo>
        <span>
            Login for
            <template v-if="assignment">{{ assignment.name }}</template>
            <template v-else>&hellip;</template>
        </span>
    </local-header>

    <div class="row justify-content-center">
        <div class="col-9">
            <b-alert v-if="error" show variant="danger">
                {{ $utils.getErrorMessage(error) }}
            </b-alert>
            <div v-else-if="assignment">
                <p>
                    Hi {{ user.readableName }},
                </p>

                <p>
                    <span v-if="canLogin">
                        Click below to login the deadline of this assignment ({{ readableDeadline }})
                    </span>
                    <span v-else>
                        You can login {{ canLoginIn }}.

                        <br />
                        Automatically login.
                        <cg-toggle v-model="autoLogin"
                                   v-if="canLoginInSeconds < 60 * 60"
                                   label-on="Yes"
                                   label-off="No"/>
                    </span>
                </p>

                <cg-submit-button :submit="login"
                                  ref="loginBtn"
                                  v-if="canLogin"
                                  @after-success="success" />
            </div>
            <cg-loader page-loader v-else />
        </div>
    </div>
</div>
</template>

<script lang="ts">
import { Vue, Component, Watch } from 'vue-property-decorator';

// @ts-ignore
import LocalHeader from '@/components/LocalHeader';
import { mapActions } from 'vuex';
import { AxiosResponse } from 'axios';

import * as models from '@/models';

@Component({
    components: { LocalHeader },
    methods: {
        ...mapActions('user', {
            storeLogin: 'login',
        }),
    },
})
export default class AssignmentLogin extends Vue {
    private assignment: models.Assignment | null = null;

    private user: models.User | null = null;

    private error: Error | null = null;

    public autoLogin: boolean = false;

    storeLogin!: (response: AxiosResponse) => Promise<unknown>;

    get assignmentId(): number {
        return parseInt(this.$route.params.assignmentId, 10);
    }

    get loginTime() {
        // Add some time for a possibly wrong clock.
        return this.assignment?.availableAt?.clone().add(15, 'seconds');
    }

    get loginUuid(): string {
        return this.$route.params.loginUuid;
    }

    get canLogin(): boolean {
        return this.loginTime?.isBefore(this.$root.$epoch) ?? false;
    }

    get canLoginInSeconds(): number | null {
        if (this.loginTime == null) {
            return null;
        }
        const now = this.$root.$epoch;
        return this.loginTime.diff(now) / 1000;
    }

    get canLoginIn(): string | null {
        const seconds = this.canLoginInSeconds;
        if (this.loginTime == null || seconds == null) {
            return null;
        }
        const now = this.$root.$epoch;
        if (seconds < 45) {
            return `${seconds.toFixed(0)} seconds`;
        } else if (seconds <= 15 * 60) {
            return this.loginTime.from(now);
        }
        return this.loginTime?.clone().local().calendar(this.$root.$epoch);
    }

    get readableDeadline(): string | null {
        if (this.assignment != null) {
            return this.$utils.readableFormatDate(this.assignment.deadline);
        }
        return null;
    }

    @Watch('canLogin')
    async onCanLoginChange() {
        if (this.canLogin && this.autoLogin) {
            this.autoLogin = false;
            const btn = await this.$waitForRef('loginBtn');
            if (btn) {
                (btn as any).onClick();
            }
        }
    }

    @Watch('assignmentId', { immediate: true })
    onAssignmentIdChange() {
        this.loadData();
    }

    @Watch('loginUuid')
    onLoginUuidChange() {
        this.loadData();
    }


    loadData() {
        this.assignment = null;
        this.user = null;
        this.error = null;

        this.$http.get(this.$utils.buildUrl(
            ['api', 'v1', 'login_links', this.loginUuid],
        )).then(({ data }) => {
            this.assignment = models.Assignment.fromServerData(data.assignment, -1, false);
            this.user = models.makeUser(data.user);
        }, err => {
            this.error = err;
        });
    }

    login() {
        return this.$http.post(this.$utils.buildUrl(['api', 'v1', 'login_links', this.loginUuid, 'login']));
    }

    success(response: AxiosResponse) {
        this.storeLogin(response).then(() => {
            this.$router.replace({ name: 'home' });
        });
    }
}
</script>
