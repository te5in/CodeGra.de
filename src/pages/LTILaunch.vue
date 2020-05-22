<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<b-alert variant="danger" show v-if="error" class="box m-0 rounded-0">
    <p style="text-align: center; font-size: 1.3em;">
        <template v-if="isCookieError">
            <p>
                We were unable to set cookies, which are necessary for CodeGrade to
                function as an LTI tool. Please allow CodeGrade to set cookies, and
                make sure that "third-party" cookies are also enabled.
            </p>

            <p v-if="cookiePostMessage">
                It might be possible to fix this automatically by clicking
                <a href="#" @click.prevent="sendPostMessage" class="inline-link">here</a>.
            </p>
        </template>
        <template v-else>
            Something went wrong during the LTI launch:
            <template v-if="errorMsg">
                {{ errorMsg }}
            </template>
            <template v-else>
                Please <a href="mailto:support@codegra.de">contact support</a>.
            </template>
        </template>
    </p>
</b-alert>
<div v-else>
    <local-header title="Opening CodeGrade" >
        <cg-logo :inverted="!darkMode" />
    </local-header>
    <cg-loader />
</div>
</template>

<script>
import 'vue-awesome/icons/times';
import { LocalHeader } from '@/components';
import { mapActions, mapGetters } from 'vuex';
import { disablePersistance } from '@/store';
import { makeProvider } from '@/lti_providers';

import { setPageTitle } from './title';

function getToastOptions() {
    return {
        position: 'bottom-center',
        closeOnSwipe: false,
        action: {
            text: '✖',
            onClick: (e, toastObject) => {
                toastObject.goAway(0);
            },
        },
    };
}

export default {
    name: 'lti-launch-page',

    data() {
        return {
            error: false,
            errorMsg: false,
            originalException: null,
        };
    },

    mounted() {
        this.secondStep(true);
    },

    computed: {
        ...mapGetters('pref', ['darkMode']),
        ...mapGetters('courses', ['assignments']),
        ...mapGetters('user', { myUserId: 'id' }),
        ...mapGetters('submissions', ['getSubmissionsByUser']),

        isCookieError() {
            return this.$utils.getProps(this.originalException, null, 'code') === 'LTI1_3_COOKIE_ERROR';
        },

        cookiePostMessage() {
            return this.$utils.getProps(this.originalException, null, 'lms_capabilities', 'cookie_post_message');
        },
    },

    methods: {
        ...mapActions('user', ['logout', 'updateAccessToken']),
        ...mapActions('courses', ['reloadCourses']),
        ...mapActions('submissions', ['forceLoadSubmissions']),
        ...mapActions('plagiarism', { clearPlagiarismCases: 'clear' }),

        secondStep(first) {
            this.$inLTI = true;

            setPageTitle('LTI is launching, please wait');

            this.$http
                .post('/api/v1/lti/launch/2?extended', {
                    jwt_token: this.$route.query.jwt,
                    blob_id: this.$route.query.blob_id,
                })
                .then(async response => {
                    const { data } = response;

                    switch (data.version) {
                    case 'v1_1':
                    case 'v1_3':
                        this.$ltiProvider = makeProvider(data.data.course.lti_provider);
                        break;
                    default:
                        return this.$utils.AssertionError.assertNever(
                            data.version,
                            `Unknown LTI version (${data.version}) encountered.`,
                        );
                    }
                    if (data.data.access_token) {
                        await this.logout();
                        disablePersistance();
                        await this.updateAccessToken(data.data.access_token);
                    } else {
                        this.clearPlagiarismCases();
                    }

                    this.$utils.WarningHeader.fromResponse(response).messages.forEach(warning => {
                        this.$toasted.info(warning.text, getToastOptions());
                    });

                    switch (data.version) {
                    case 'v1_1':
                    case 'v1_3':
                        return this.handleLTI(data.data);
                    default:
                        return this.$utils.AssertionError.assertNever(
                            data.version,
                            `Unknown LTI version (${data.version}) encountered.`,
                        );
                    }
                })
                .catch(err => {
                    if (first && this.$utils.getProps(err, null, 'response', 'status') === 401) {
                        return this.logout().then(() => this.secondStep(false));
                    }
                    this.errorMsg = this.$utils.getErrorMessage(err, null);
                    this.originalException = this.$utils.getProps(err, null, 'response', 'data', 'original_exception');
                    this.error = true;

                    return null;
                });
        },

        async handleLTI(data) {
            if (data.type !== 'normal_result') {
                throw new Error(`Unknown LTI1.1 type: ${data.type}.`);
            }
            if (!this.assignments[data.assignment.id]) {
                await this.reloadCourses();
            }
            this.$LTIAssignmentId = data.assignment.id;

            if (data.new_role_created) {
                this.$toasted.info(
                    `You do not have any permissions yet, please ask your teacher to enable them for your role "${
                        data.new_role_created
                    }".`,
                    getToastOptions(),
                );
            }

            if (data.updated_email) {
                this.$toasted.info(
                    `Your email was updated to "${
                        data.updated_email
                    }" which is the email registered with your ${data.custom_lms_name}.`,
                    getToastOptions(),
                );
            }

            if (this.$route.query.redirect && this.$route.query.redirect.startsWith('/')) {
                return this.$router.replace(this.$route.query.redirect);
            } else if (this.$route.query.goto_latest_submission) {
                const assignment = this.assignments[data.assignment.id];
                if (!assignment || !assignment.course.isStudent) {
                    return this.doDefaultRedirect(data);
                }

                await this.forceLoadSubmissions(assignment.id);
                const subs = this.getSubmissionsByUser(assignment.id, this.myUserId, {
                    includeGroupSubmissions: true,
                });

                if (!subs || subs.length === 0) {
                    return this.doDefaultRedirect(data);
                }

                return this.$router.replace({
                    name: 'submission',
                    params: {
                        courseId: assignment.courseId,
                        assignmentId: assignment.id,
                        submissionId: subs[subs.length - 1].id,
                    },
                });
            } else {
                return this.doDefaultRedirect(data);
            }
        },

        doDefaultRedirect(data) {
            return this.$router.replace({
                name: 'assignment_submissions',
                params: {
                    courseId: data.assignment.course.id,
                    assignmentId: data.assignment.id,
                },
            });
        },

        sendPostMessage() {
            const { host, protocol } = window.location;
            window.parent.postMessage({
                messageType: this.cookiePostMessage,
                data: this.$utils.buildUrl(
                    ['api', 'v1', 'lti1.3', 'launch'],
                    { host, protocol },
                ),
            }, '*');
        },
    },

    components: {
        LocalHeader,
    },
};
</script>

<style lang="less" scoped>
.box {
    display: flex;
    justify-content: center;
    align-items: center;
}

.cg-logo {
    height: 1.5rem;
    width: auto;
}
</style>
