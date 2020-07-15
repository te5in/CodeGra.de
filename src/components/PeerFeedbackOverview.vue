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
                <td>This is the list of all students that you should give peer feedback to.</td>
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
