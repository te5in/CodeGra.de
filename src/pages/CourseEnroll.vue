<template>
<div class="course-enroll">
    <local-header show-logo>
        <template #title>
            Enroll in
            <template v-if="link">
                {{ link.course.name }}
            </template>
            <template v-else>
                &hellip;
            </template>
        </template>
    </local-header>

    <b-alert v-if="error" variant="danger" show class="m-3">
        {{ $utils.getErrorMessage(error) }}
    </b-alert>

    <div class="justify-content-center row" v-else-if="link">
        <div class="text-center pb-2">
            <h6>You have been invited to join the course {{ link.course.name }}.</h6>
        </div>
        <div class="d-flex justify-content-around col-12 row">
            <div class="col-lg-6 mb-3">
                <b-card v-if="loggedIn && !loggingIn">
                    <template #header>
                        <div>
                            <span>Join as logged in user</span>

                            <a href="#"
                               class="inline-link float-right"
                               @click.prevent="storeLogout">Logout</a>
                        </div>
                    </template>
                    <div class="text-center">
                        <div v-b-popover.top.hover="alreadyInCourse ? 'The current user is already enrolled in this course.' : ''">
                            <cg-submit-button :submit="joinWithCurrentAccount"
                                              @after-success="afterJoin"
                                              :disabled="alreadyInCourse"
                                              label="Join" />
                        </div>
                    </div>
                </b-card>

                <b-card header="Login and join" v-else>
                    <b-form @submit="() => $refs.login.onClick()">
                        <b-form-group
                            label="Username:"
                            :id="`login-username-input-group-${uniqueId}`"
                            :label-for="`login-username-input-${uniqueId}`">
                            <input type="text"
                                   :id="`login-username-input-${uniqueId}`"
                                   class="form-control"
                                   placeholder="Enter username"
                                   v-model="loginData.username"
                                   @keyup.enter="() => $refs.login.onClick()"/>
                        </b-form-group>

                        <b-form-group
                            label="Password:"
                            :id="`login-password-input-group-${uniqueId}`"
                            :label-for="`login-password-input-${uniqueId}`">
                            <input :id="`login-password-input-${uniqueId}`"
                                   type="password"
                                   v-model="loginData.password"
                                   class="form-control"
                                   @keyup.enter="() => $refs.login.onClick()"
                                   placeholder="Enter your password"/>
                        </b-form-group>

                        <cg-submit-button
                            @after-success="afterJoin"
                            class="float-right"
                            ref="login"
                            label="Login and join"
                            :submit="loginAndJoin" />
                    </b-form>

                </b-card>
            </div>

            <div class="col-lg-6">
                <b-card header="Join as a new user">
                    <register :registration-url="registrationUrl"
                              :new-route="newRoute"/>
                </b-card>
            </div>
        </div>
    </div>
    <cg-loader v-else page-loader />
</div>
</template>

<script lang="ts">
    import { Vue, Component, Watch } from 'vue-property-decorator';
import { mapGetters, mapActions } from 'vuex';

// @ts-ignore
import LocalHeader from '@/components/LocalHeader';
// @ts-ignore
import Register from '@/components/Register';

import { setPageTitle } from './title';

@Component({
    components: { LocalHeader, Register },
    computed: {
        ...mapGetters('user', {
            loggedIn: 'loggedIn',
            loggedInUsername: 'username',
        }),
        ...mapGetters('courses', {
            allCourses: 'courses',
        }),
    },
    methods: {
        ...mapActions('user', {
            storeLogin: 'login',
            storeLogout: 'logout',
        }),
        ...mapActions('courses', ['reloadCourses']),
    },
})
export default class CourseEnroll extends Vue {
    private link: Record<string, any> | null = null;

    private error: Error | null = null;

    private uniqueId: string = `${this.$utils.getUniqueId()}`;

    private loginData: { username: string, password: string } = {
        username: '',
        password: '',
    };

    private loggingIn: boolean = false;

    readonly loggedIn!: boolean;

    readonly loggedInUsername!: string | null;

    readonly storeLogin!: (data: any) => Promise<unknown>;

    readonly storeLogout!: () => Promise<unknown>;

    readonly reloadCourses!: () => Promise<unknown>;

    readonly allCourses!: Record<number, unknown>;

    get courseId(): number {
        return parseInt(this.$route.params.courseId, 10);
    }

    get linkId(): string {
        return this.$route.params.linkId;
    }

    get newRoute() {
        return {
            name: 'home',
            query: {
                sbloc: 'm',
                filter: this.link?.course.name,
            },
        };
    }

    afterJoin() {
        this.$router.push(this.newRoute);
    }

    joinWithCurrentAccount() {
        if (this.link == null) {
            return Promise.reject(new Error('Link not found'));
        }

        return this.$http.post(
            this.$utils.buildUrl(
                ['api', 'v1', 'courses', this.link.course.id, 'registration_links', this.link.id, 'join'],
            ),
        ).then(async res => {
            await this.reloadCourses();
            return res;
        });
    }

    async loginAndJoin() {
        this.loggingIn = true;
        try {
            const response = await this.$http.post('/api/v1/login?with_permissions', this.loginData);

            return [
                response,
                await this.storeLogin(response),
                await this.joinWithCurrentAccount().catch(async err => {
                    await this.storeLogout();
                    throw err;
                }),
            ];
        } finally {
            this.loggingIn = false;
        }
    }

    get registrationUrl() {
        if (this.link == null) {
            return null;
        }
        return this.$utils.buildUrl(
            ['api', 'v1', 'courses', this.link.course.id, 'registration_links', this.link.id, 'user'],
        );
    }

    get alreadyInCourse() {
        if (this.link == null) {
            return false;
        }
        return this.link.course.id in this.allCourses;
    }

    @Watch('link', { immediate: true })
    onLinkChange() {
        if (this.link) {
            setPageTitle(`Enroll in ${this.link.course.name}`);
        } else {
            setPageTitle('Enroll in ...');
        }
    }

    @Watch('courseId', { immediate: true })
    @Watch('linkId')
    async loadData() {
        this.link = null;
        this.error = null;

        try {
            this.link = (await this.$http.get(this.$utils.buildUrl([
                'api', 'v1', 'courses', this.courseId, 'registration_links', this.linkId,
            ]))).data;
        } catch (error) {
            this.error = error;
        }
    }
}
</script>
