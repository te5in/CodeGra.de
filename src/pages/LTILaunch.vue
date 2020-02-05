<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
    <b-alert variant="danger" show v-if="error" class="box m-0 rounded-0">
        <p style="text-align: center; font-size: 1.3em;">
            Something went wrong during the LTI launch:
            <template v-if="errorMsg">
                {{ errorMsg }}
            </template>
            <template v-else>
                Please <a href="mailto:support@codegra.de">contact support</a>.
            </template>
        </p>
    </b-alert>
    <loader v-else/>
</template>

<script>
import 'vue-awesome/icons/times';
import { Loader } from '@/components';
import { mapActions } from 'vuex';
import { disablePersistance } from '@/store';
import ltiProviders from '@/lti_providers';

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
        };
    },

    mounted() {
        this.secondStep(true);
    },

    methods: {
        ...mapActions('user', ['logout', 'updateAccessToken']),
        ...mapActions('plagiarism', { clearPlagiarismCases: 'clear' }),

        secondStep(first) {
            this.$inLTI = true;

            setPageTitle('LTI is launching, please wait');

            this.$http
                .post('/api/v1/lti/launch/2', {
                    jwt_token: this.$route.query.jwt,
                    blob_id: this.$route.query.blob_id,
                })
                .then(
                    async response => {
                        const { data } = response;

                        this.$ltiProvider = ltiProviders[data.data.custom_lms_name];
                        if (data.data.access_token) {
                            await this.logout();
                            disablePersistance();
                            await this.updateAccessToken(data.data.access_token);
                        } else {
                            this.clearPlagiarismCases();
                        }

                        this.$utils.WarningHeader.fromResponse(response).messages.forEach(
                            warning => {
                                this.$toasted.info(warning.text, getToastOptions());
                            },
                        );

                        this.$ltiProvider = ltiProviders[data.data.custom_lms_name];

                        switch (data.version) {
                            case 'lti_v1_1': return this.handleLTI1p1(data.data);
                            default: throw new Error(`Unknown LTI version (${data.version}) encountered.`);
                        }
                    },
                )
                .catch(err => {
                    if (err.response) {
                        if (first && err.response.status === 401) {
                            return this.logout().then(() => this.secondStep(false));
                        }
                    }
                    this.errorMsg = this.$utils.getErrorMessage(err, null);
                    this.error = true;

                    return null;
                });
        },

        handleLTI1p1(data) {
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
                    }" which is the email registered with your ${
                        data.custom_lms_name
                    }.`,
                    getToastOptions(),
                );
            }
            if (
                this.$route.query.redirect &&
                    this.$route.query.redirect.startsWith('/')
            ) {
                this.$router.replace(this.$route.query.redirect);
            } else {
                this.$router.replace({
                    name: 'assignment_submissions',
                    params: {
                        courseId: data.assignment.course.id,
                        assignmentId: data.assignment.id,
                    },
                });
            }
        },
    },

    components: {
        Loader,
    },
};
</script>

<style>
.box {
    display: flex;
    justify-content: center;
    align-items: center;
}
</style>
