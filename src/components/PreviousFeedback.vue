<template>
<div class="previous-feedback d-flex flex-column">
    <div class="overflow-auto h-100">
        <div class="p-3 sticky-top bg-light border-bottom">
            <b-input-group>
                <input :value="filter"
                       @change="filter = $event.target.value"
                       class="form-control"
                       placeholder="Filter on comment or author"/>

                <b-input-group-append>
                    <b-button variant="primary"
                              class="settings-button"
                              @click="settingsCollapsed = !settingsCollapsed"
                              v-b-popover.top.hover.window="'Show settings'">
                        <fa-icon name="gear"
                                 :class="{ rotate: settingsCollapsed }"/>
                    </b-button>
                </b-input-group-append>
            </b-input-group>

            <collapse :collapsed="settingsCollapsed">
                <hr class="mb-2"/>

                <b-form-group class="mb-0"
                              label="Context lines">
                    <cg-number-input
                        v-model="contextLines"
                        placeholder="Context lines"/>
                </b-form-group>
            </collapse>
        </div>

        <b-alert show
                 variant="danger"
                 v-if="error != null">
            {{ error }}
        </b-alert>

        <cg-loader v-else-if="loading"
                   class="p-3" />

        <div v-else-if="sortedOtherSubmissions.length === 0"
            class="p-3 text-muted font-italic">
            No submissions to other assignments in this course.
        </div>

        <ol v-else
            class="mb-0 pl-0">
            <li v-for="(sub, i) in sortedOtherSubmissions"
                :key="sub.id"
                class="border-top">
                <collapse :collapsed="shouldCollapse(sub)">
                    <h6 slot="handle"
                        v-b-toggle="`previous-feedback-collapse-${sub.id}`"
                        class="assignment-name p-3 mb-0 cursor-pointer"
                        :class="{
                            'text-muted': !hasFeedback(sub),
                        }">
                        <div class="caret mr-2 float-left">
                            <fa-icon name="chevron-down" :scale="0.75" />
                        </div>

                        {{ sub.assignment.name }}

                        <span v-if="sub.grade != null"
                              class="font-italic">
                            (graded: {{ sub.grade }})
                        </span>

                        <span v-else
                              class="text-muted font-italic">
                            (not yet graded)
                        </span>

                        <span class="float-right">
                            <cg-loader :scale="1" v-if="sub.feedback == null" />

                            <b-badge v-else
                                     :variant="hasFeedback(sub) ? 'primary' : 'secondary'"
                                     title="Comments on this submission">
                                <template v-if="filter">
                                    {{ filteredFeedbackCounts[sub.id] }} /
                                </template>

                                {{ totalFeedbackCounts[sub.id] }}
                            </b-badge>
                        </span>
                    </h6>

                    <div v-if="sub.feedback != null && !hasFeedback(sub)"
                         class="p-3 border-top text-muted font-italic">
                        <template v-if="filter" >
                            No comments match the filter.
                        </template>

                        <template v-else>
                            No feedback given.
                        </template>
                    </div>

                    <feedback-overview
                        v-else
                        :assignment="sub.assignment"
                        :submission="sub"
                        show-inline-feedback
                        :non-editable="true"
                        :context-lines="contextLines"
                        :should-render-general="shouldRenderGeneral"
                        :should-render-thread="shouldRenderThread"
                        :should-fade-reply="shouldFadeReply"
                        open-files-in-new-tab/>
                </collapse>
            </li>
        </ol>
    </div>
</div>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';

import 'vue-awesome/icons/chevron-down';
import 'vue-awesome/icons/gear';

import { Submission } from '@/models';
import { Search } from '@/utils/search';
import { defaultdict } from '@/utils/defaultdict';
import { flatMap1 } from '@/utils';

import { FeedbackOverview } from '@/components';

import Collapse from '@/components/Collapse';

const GeneralFeedbackSearcher = new Search(['comment', 'author']);

const InlineFeedbackSearcher = new Search(['comment', 'author']);

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
            filter: '',
            latestSubsInCourse: [],
            settingsCollapsed: true,
            contextLines: 3,
        };
    },

    computed: {
        ...mapGetters('users', ['getUser']),

        course() {
            return this.assignment.course;
        },

        assignment() {
            return this.submission.assignment;
        },

        author() {
            return this.submission.user;
        },

        otherSubmissions() {
            return this.latestSubsInCourse.filter(sub => sub.id !== this.submission.id);
        },

        sortedOtherSubmissions() {
            return [...this.otherSubmissions].sort((a, b) => {
                if (this.filter) {
                    const hasA = this.hasFeedback(a);
                    const hasB = this.hasFeedback(b);

                    if (hasA ^ hasB) {
                        return hasA ? -1 : 1;
                    }
                }

                return a.assignment.deadline.isBefore(
                    b.assignment.deadline,
                ) ? 1 : -1;
            });
        },

        searchableGeneralFeedback() {
            return this.otherSubmissions.map(sub => ({
                comment: sub.comment,
                author: sub.comment_author.readableName,
                sub,
            }));
        },

        filteredGeneralFeedback() {
            return GeneralFeedbackSearcher.search(
                this.filter,
                this.searchableGeneralFeedback,
            ).reduce((acc, { sub }) => {
                acc.add(sub.id);
                return acc;
            }, new Set());
        },

        searchableUserFeedback() {
            return this.otherSubmissions.reduce((acc, sub) => {
                if (sub.feedback == null) {
                    return acc;
                }

                return acc.concat(
                    flatMap1(
                        Object.values(sub.feedback.user),
                        fileFb => flatMap1(
                            Object.values(fileFb),
                            thread => thread.replies.map(reply => ({
                                comment: reply.message,
                                author: this.getUser(reply.authorId).readableName,
                                thread,
                                reply,
                            })),
                        ),
                    ),
                );
            }, []);
        },

        filteredUserFeedback() {
            return this.otherSubmissions.reduce(
                (acc, sub) => Object.assign(acc, this.filterUserFeedback(sub.feedback)),
                {},
            );
        },

        filteredFeedbackCounts() {
            return this.otherSubmissions.reduce((acc, sub) => {
                const fb = sub.feedback;
                if (fb == null) {
                    return acc;
                }

                const general = this.shouldRenderGeneral(sub) ? 1 : 0;
                const threads = this.$utils.flatMap1(
                    Object.values(sub.feedback.user),
                    fileFb => Object.values(fileFb),
                ).filter(thread =>
                    this.shouldRenderThread(thread),
                );
                acc[sub.id] = general + threads.length;
                return acc;
            }, {});
        },

        totalFeedbackCounts() {
            return this.otherSubmissions.reduce((acc, sub) => {
                const fb = this.$utils.getProps(sub, null, 'feedback');
                if (fb != null) {
                    acc[sub.id] = fb.countEntries();
                }
                return acc;
            }, {});
        },
    },

    watch: {
        submission: {
            immediate: true,
            handler(newSub) {
                if (!this.latestSubsInCourse.find(s => s.id === newSub.id)) {
                    this.loadOtherFeedback(this.submission.id);
                }
            },
        },
    },

    methods: {
        ...mapActions('submissions', [
            'loadLatestByUserInCourse',
        ]),
        ...mapActions('feedback', [
            'loadFeedback',
        ]),

        loadOtherFeedback() {
            this.loading = true;
            this.error = null;
            this.latestSubsInCourse = [];

            this.loadLatestByUserInCourse({
                courseId: this.course.id,
                userId: this.author.id,
            }).then(
                subs =>
                    Promise.all(
                        subs.map(sub =>
                            this.loadFeedback({
                                assignmentId: this.assignmentId,
                                submissionId: sub.id,
                            }),
                        ),
                    ).then(
                        () => {
                            this.latestSubsInCourse = subs;
                            this.loading = false;
                        },
                        err => {
                            this.error = this.$utils.getErrorMessage(err);
                            this.loading = false;
                        },
                    ),
            );
        },

        filterUserFeedback(feedback) {
            // TODO: We filter only on the content of comments. Do we also
            // want to filter on filename? Or on username, so you can quickly
            // see all comments by a user? Or on other things?

            if (feedback == null) {
                return null;
            }

            let filteredFb = this.searchableUserFeedback;

            if (this.filter != null && this.filter !== '') {
                filteredFb = InlineFeedbackSearcher.search(this.filter, filteredFb);
            }

            return filteredFb.reduce((acc, { thread, reply }) => {
                acc[thread.id].add(reply.id);
                return acc;
            }, defaultdict(() => new Set()));
        },

        shouldRenderGeneral(sub) {
            return this.filteredGeneralFeedback.has(sub.id);
        },

        shouldRenderThread(thread) {
            return this.$utils.getProps(
                this.filteredUserFeedback,
                null,
                thread.id,
            ) != null;
        },

        shouldFadeReply(thread, reply) {
            return this.shouldRenderThread(thread) &&
                !this.filteredUserFeedback[thread.id].has(reply.id);
        },

        shouldCollapse(sub) {
            if (this.filter) {
                return this.filteredFeedbackCounts[sub.id] === 0;
            } else {
                return true;
            }
        },

        hasFeedback(sub) {
            if (this.filter) {
                return this.filteredFeedbackCounts[sub.id] > 0;
            } else {
                return this.totalFeedbackCounts[sub.id] > 0;
            }
        },
    },

    components: {
        Collapse,
        FeedbackOverview,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

ol {
    list-style-type: none;

    li:first-child {
        border-top: 0 !important;
    }
}

.caret {
    transform: rotate(0);
    transition: transform @transition-duration;
}

.x-collapsed .caret,
.x-collapsing .caret {
    transform: rotate(-90deg);
}

.settings-button {
    .fa-icon {
        transform: translateY(-1px) rotate(0);
        transition: transform (2 * @transition-duration);

        &.rotate {
            transform: translateY(-1px) rotate(-90deg);
        }
    }
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
