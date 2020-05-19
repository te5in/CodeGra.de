<template>
<div class="course-feedback d-flex flex-column">
    <div class="overflow-auto h-100">
        <div class="p-3 sticky-top bg-light border-bottom">
            <b-input-group>
                <input :value="filter"
                       @change="filter = $event.target.value"
                       class="form-control"
                       placeholder="Filter on comment or author"/>

                <b-input-group-append>
                    <b-button variant="secondary"
                              class="settings-button"
                              @click="settingsCollapsed = !settingsCollapsed"
                              v-b-popover.top.hover.window="`${settingsCollapsed ? 'Show' : 'Hide'} settings`">
                        <fa-icon name="gear"
                                 :class="{ rotate: settingsCollapsed }"/>
                    </b-button>
                </b-input-group-append>
            </b-input-group>

            <collapse :collapsed="settingsCollapsed">
                <hr class="mb-2"/>

                <b-form-group label="Context lines">
                    <cg-number-input
                        v-model="contextLines"
                        placeholder="Context lines"/>
                </b-form-group>

                <b-input-group class="mb-0">
                    <b-input-group-prepend is-text>
                        <b-form-checkbox
                            v-model="hideAutoTestRubricCategories"
                            :id="`course-feedback-hide-at-rubric-${id}`"
                            class="mr-n2"/>
                    </b-input-group-prepend>

                    <div class="form-control">
                        <label :for="`course-feedback-hide-at-rubric-${id}`"
                               class="mb-0 d-block cursor-pointer">
                            Hide AutoTest rubric categories
                        </label>
                    </div>
                </b-input-group>
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
                        v-b-toggle="`course-feedback-collapse-${sub.id}`"
                        class="assignment-name p-3 mb-0 cursor-pointer"
                        :class="{
                            'text-muted': !hasFeedbackMatches(sub),
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
                                     :variant="hasFeedbackMatches(sub) ? 'primary' : 'secondary'"
                                     title="Comments on this submission">
                                <template v-if="filter">
                                    {{ filteredFeedbackCounts[sub.id] }} /
                                </template>

                                {{ totalFeedbackCounts[sub.id] }}
                            </b-badge>
                        </span>
                    </h6>

                    <div v-if="rubricResultsBySub[sub.id] != null"
                         class="px-3 pb-3">
                        <span v-for="{ result, row, item } in filteredRubricResults[sub.id]"
                              :key="`${sub.id}-${item.id}`">
                            <b-badge
                                :id="`course-feedback-rubric-item-${id}-${sub.id}-${item.id}`"
                                pill
                                class="mr-1"
                                variant="secondary">
                                <span class="mr-1">{{ row.header }}</span>
                                <sup>{{ item.achieved_points }}</sup>&frasl;<sub>{{ row.maxPoints }}</sub>

                                <template v-if="row.locked === 'auto_test'">
                                    <span class="mx-1">|</span> AT
                                </template>
                            </b-badge>

                            <b-popover
                                triggers="click hover"
                                placement="top"
                                :target="`course-feedback-rubric-item-${id}-${sub.id}-${item.id}`"
                                custom-class="course-feedback-rubric-row-popover">
                                <component
                                    :is="`rubric-viewer-${row.type}-row`"
                                    :value="result"
                                    :rubric-row="row"
                                    :assignment="sub.assignment"/>
                            </b-popover>
                        </span>
                    </div>

                    <div v-if="!hasFeedbackMatches(sub)"
                         class="p-3 border-top text-muted font-italic">
                        <template v-if="filter">
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
                        :open-files-in-new-tab="!$inLTI">
                        <template v-if="filter" #no-inline-feedback>
                            No inline feedback matching the filter.
                        </template>
                    </feedback-overview>
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

import { Submission, User } from '@/models';
import { Search } from '@/utils/search';
import { defaultdict } from '@/utils/defaultdict';
import { flatMap1, filterMap, Just, Nothing } from '@/utils';
import { NONEXISTENT } from '@/constants';

import { FeedbackOverview } from '@/components';

import Collapse from './Collapse';
import RubricViewerNormalRow from './RubricViewerNormalRow';
import RubricViewerContinuousRow from './RubricViewerContinuousRow';

const GeneralFeedbackSearcher = new Search(['comment', 'author']);

const InlineFeedbackSearcher = new Search(['comment', 'author']);

export default {
    name: 'course-feedback',

    props: {
        course: {
            type: Object,
            required: true,
        },
        user: {
            type: User,
            required: true,
        },
        excludeSubmission: {
            type: Submission,
            default: null,
        },
    },

    data() {
        return {
            id: this.$utils.getUniqueId(),
            loading: true,
            error: null,
            filter: '',
            latestSubsInCourse: [],
            settingsCollapsed: true,
            contextLines: 3,
            hideAutoTestRubricCategories: true,
        };
    },

    computed: {
        ...mapGetters('users', ['getUser']),
        ...mapGetters('rubrics', {
            allRubrics: 'rubrics',
            rubricResults: 'results',
        }),

        courseId() {
            return this.course.id;
        },

        userId() {
            return this.user.id;
        },

        otherSubmissions() {
            const excluded = this.excludeSubmission;
            if (excluded == null) {
                return this.latestSubsInCourse;
            }
            return this.latestSubsInCourse.filter(sub => sub.id !== excluded.id);
        },

        sortedOtherSubmissions() {
            return [...this.otherSubmissions].sort((a, b) => {
                if (this.filter) {
                    const hasA = this.hasFeedbackMatches(a);
                    const hasB = this.hasFeedbackMatches(b);

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

        rubricResultsBySub() {
            return this.otherSubmissions.reduce((acc, sub) => {
                if (this.allRubrics[sub.assignmentId] === NONEXISTENT) {
                    return acc;
                }
                const result = this.$utils.getProps(this.rubricResults, null, sub.id);
                if (Object.values(result.selected).length > 0) {
                    acc[sub.id] = result;
                }
                return acc;
            }, {});
        },

        filteredRubricResults() {
            return this.otherSubmissions.reduce((acc, sub) => {
                const rubric = this.allRubrics[sub.assignmentId];
                const result = this.rubricResultsBySub[sub.id];

                if (rubric == null || result == null) {
                    return acc;
                }

                // Loop over the rubric rows to ensure the same order as the rubric viewer.
                const items = filterMap(rubric.rows, row => {
                    const item = result.selected[row.id];
                    if (item == null) {
                        return Nothing;
                    }
                    if (this.hideAutoTestRubricCategories && row.locked === 'auto_test') {
                        return Nothing;
                    }
                    return Just({ result, row, item });
                });

                if (items.length > 0) {
                    acc[sub.id] = items;
                }
                return acc;
            }, {});
        },
    },

    watch: {
        courseId: {
            immediate: true,
            handler() {
                this.loadCourseFeedback();
            },
        },

        userId: {
            immediate: true,
            handler() {
                this.loadCourseFeedback();
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
        ...mapActions('rubrics', {
            loadRubric: 'loadRubric',
            loadRubricResult: 'loadResult',
        }),

        loadCourseFeedback() {
            if (
                this.latestSubsInCourse.length > 0 &&
                this.latestSubsInCourse.every(sub =>
                    sub.course === this.course && sub.user === this.user,
                )
            ) {
                this.loading = false;
                return;
            }

            this.loading = true;
            this.error = null;
            this.latestSubsInCourse = [];

            this.loadLatestByUserInCourse({
                courseId: this.course.id,
                userId: this.user.id,
            }).then(
                subs => {
                    this.latestSubsInCourse = subs;
                    return Promise.all(
                        flatMap1(subs, sub => ([
                            this.loadFeedback({
                                assignmentId: sub.assignmentId,
                                submissionId: sub.id,
                            }),
                            this.loadRubric({
                                assignmentId: sub.assignmentId,
                            }).catch(this.$utils.makeHttpErrorHandler({
                                // Assignment may not have a rubric.
                                404: () => ({}),
                            })),
                            this.loadRubricResult({
                                assignmentId: sub.assignmentId,
                                submissionId: sub.id,
                            }),
                        ])),
                    );
                },
            ).catch(err => {
                this.error = this.$utils.getErrorMessage(err);
            }).then(() => {
                this.loading = false;
            });
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

        hasFeedbackMatches(sub) {
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
        RubricViewerNormalRow,
        RubricViewerContinuousRow,
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

.card {
    border-left: none !important;
    border-right: none !important;
    border-bottom: none !important;
    border-radius: 0 !important;
}
</style>

<style lang="less">
.course-feedback .feedback-overview {
    border-left: none !important;
    border-right: none !important;
    border-bottom: none !important;
    border-radius: 0 !important;

    .scroller > .card {
        border-radius: 0 !important;
    }
}

.course-feedback-rubric-row-popover {
    max-width: 35rem;

    .popover-body {
        text-align: left;
        padding: 0 !important;
    }

    .row-description p {
        margin-bottom: 0.5rem !important;
    }

    .rubric-item .description {
        max-height: 10rem;
    }
}
</style>
