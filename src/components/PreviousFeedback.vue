<template>
<cg-loader v-if="loading" />

<b-alert show
         variant="danger"
         v-else-if="error != null">
    {{ error }}
</b-alert>

<ol v-else
    class="previous-feedback pl-0 border-top">
    <li v-for="(sub, i) in sortedOtherSubmissions"
        v-if="sub.id !== submission.id"
        :key="sub.id"
        class="border-bottom">

        <collapse :collapsed="i > 0">
            <h4 slot="handle"
                v-b-toggle="`previous-feedback-collapse-${sub.id}`"
                class="p-3 mb-0 cursor-pointer"
                :class="{
                    'text-muted': feedbackCounts[sub.id] === 0,
                }">
                <div class="caret mr-2 float-left">+</div>
                {{ sub.assignment.name }}
                {{ sub.assignment.readableDeadline }}

                <small class="float-right">
                    <cg-loader :scale="1" v-if="feedbackCounts[sub.id] == null" />

                    <b-badge v-else
                             variant="primary"
                             title="Comments on this submission">
                        {{ feedbackCounts[sub.id] }}
                    </b-badge>
                </small>
            </h4>

            <feedback-overview
                :assignment="sub.assignment"
                :submission="sub"
                show-inline-feedback
                :non-editable="true" />
        </collapse>
    </li>
</ol>
</template>

<script>
import { mapActions } from 'vuex';

import { Submission } from '@/models';

import { FeedbackOverview } from '@/components';

import Collapse from '@/components/Collapse';

export default {
    name: 'previous-feedback',

    props: {
        submission: {
            type: Submission,
            required: true,
        },
    },

    data() {
        return {
            loading: true,
            error: null,
            otherSubmissions: [],
        };
    },

    computed: {
        course() {
            return this.assignment.course;
        },

        assignment() {
            return this.submission.assignment;
        },

        author() {
            return this.submission.user;
        },

        sortedOtherSubmissions() {
            return this.otherSubmissions.sort((a, b) =>
                (a.assignment.deadline.isBefore(
                    b.assignment.deadline,
                ) ? 1 : -1),
            );
        },

        feedbackCounts() {
            return this.otherSubmissions.reduce((acc, sub) => {
                acc[sub.id] = this.countEntries(sub.feedback);
                return acc;
            }, {});
        },
    },

    watch: {
        submission: {
            immediate: true,
            handler(newSub) {
                if (!this.otherSubmissions.find(s => s.id === newSub.id)) {
                    this.loadOtherFeedback(this.submission.id);
                }
            },
        },
    },

    methods: {
        ...mapActions('submissions', [
            'loadLatestByUserInCourse',
        ]),

        loadOtherFeedback() {
            this.loading = true;
            this.error = null;
            this.otherSubmissions = [];

            this.loadLatestByUserInCourse({
                courseId: this.course.id,
                userId: this.author.id,
            }).then(
                subs => {
                    this.otherSubmissions = subs;
                    this.loading = false;
                },
                err => {
                    this.error = this.$utils.getErrorMessage(err);
                    this.loading = false;
                },
            );
        },

        countEntries(feedback) {
            if (feedback == null) {
                return null;
            }
            return feedback.countEntries() + (this.submission.comment ? 1 : 0);
        },
    },

    mounted() {
    },

    destroyed() {
    },

    components: {
        Collapse,
        FeedbackOverview,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.previous-feedback {
    list-style-type: none;
}

.caret {
    transform: rotate(0);
    transition: transform @transition-duration;
}

.x-collapsed .caret,
.x-collapsing .caret {
    transform: rotate(-90deg);
}
</style>

<style lang="less">
.previous-feedback .feedback-overview {
    border-left: none !important;
    border-right: none !important;
    border-bottom: none !important;
    border-radius: 0 !important;

    .scroller > .card {
        border-radius: 0 !important;
    }
}
</style>
