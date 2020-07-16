<template>
<div class="peer-feedback-overview">
    <table class="table table-striped table-hover">
        <thead>
            <tr>
                <th>User</th>
            </tr>
        </thead>

        <tbody>
            <tr v-for="sub in submissions" :key="sub.id"
                @click="gotoSubmission(sub)">
                <td><cg-user :user="sub.user" /></td>
            </tr>
        </tbody>

        <tfoot>
            <tr>
                <td>
                    This lists all the students that you have been assigned to
                    give peer feedback.

                    <template v-if="peerFeedbackDeadline != null">
                        You have until {{ peerFeedbackDeadline }} to complete
                        your feedback.
                    </template>
                </td>
            </tr>
        </tfoot>
    </table>
</div>
</template>

<script>
import { mapGetters } from 'vuex';
import * as models from '@/models';

export default {
    name: 'peer-feedback-overview',

    props: {
        assignment: {
            type: models.Assignment,
            required: true,
        },
    },

    computed: {
        ...mapGetters('user', {
            userId: 'id',
            userPerms: 'permissions',
        }),
        ...mapGetters('submissions', ['getLatestSubmissions']),

        submissions() {
            return this.$utils.sortBy(
                this.getLatestSubmissions(this.assignment.id).filter(
                    s => s.user.id !== this.userId,
                ),
                sub => [sub.user.readableName],
            );
        },

        peerFeedbackDeadline() {
            if (this.assignment.peerFeedbackDeadline == null) {
                return null;
            }
            return this.$utils.readableFormatDate(this.assignment.peerFeedbackDeadline);
        },
    },

    methods: {
        gotoSubmission(sub) {
            this.$router.push({
                name: 'submission',
                params: { submissionId: sub.id },
                query: {
                    peerFeedback: true,
                },
            });
        },
    },
};
</script>
