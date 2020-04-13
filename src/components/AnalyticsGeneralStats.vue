<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<b-card class="analytics-general-stats"
        :class="{ large }"
        :header="large ? 'General statistics' : ''"
        :body-class="cardBodyClass"
        >
    <div class="border-right metric">
        <component :is="metricTag"class="d-block">
            {{ studentCount }}
        </component>

        <label>{{ $utils.capitalize(studentType) }}s</label>
    </div>

    <div class="border-right metric">
        <component :is="metricTag" class="d-block">
            {{ submissionCount }}
        </component>

        <label>Submissions</label>
    </div>

    <div class="border-right metric">
        <component :is="metricTag"
                    class="d-block">

            <span v-if="gradeStats == null">
                -
            </span>

            <span v-else class="position-relative">
                {{ to1Dec(gradeStats.mean) }}

                <span class="extra text-muted">
                    &pm;{{ to1Dec(gradeStats.stdev) }}
                </span>
            </span>
        </component>

        <label v-if="large">Average grade</label>
        <label v-else>Avg. grade</label>

        <description-popover v-if="large"
                             triggers="hover"
                             placement="top">
            The average grade over the latest submissions that have already
            been graded.

            <table v-if="gradeStats != null"
                   class="table mt-2 mb-0">
                <tr>
                    <td>Mean</td>
                    <td class="text-right">
                        {{ to2Dec(gradeStats.mean) }}
                    </td>
                </tr>
                <tr>
                    <td>Std. deviation</td>
                    <td class="text-right">
                        {{ to2Dec(gradeStats.stdev) }}
                    </td>
                </tr>
                <tr>
                    <td>Median</td>
                    <td class="text-right">
                        {{ to2Dec(gradeStats.median) }}
                    </td>
                </tr>
                <tr>
                    <td>Mode</td>
                    <td class="text-right">
                        {{ to2Dec(gradeStats.mode) }}
                    </td>
                </tr>
            </table>
        </description-popover>
    </div>

    <div class="border-right metric">
        <component :is="metricTag" class="d-block">
            <span v-if="submissionStats == null">
                -
            </span>

            <span v-else class="position-relative">
                {{ to1Dec(submissionStats.mean) }}

                <span class="extra text-muted">
                    &pm;{{ to1Dec(submissionStats.stdev) }}
                </span>
            </span>
        </component>

        <label v-if="large">Average submissions</label>
        <label v-else>Avg. subs.</label>

        <description-popover v-if="large"
                             triggers="hover"
                             placement="top">
            The average number of submissions per {{ studentType }}.

            <table v-if="submissionStats != null"
                   class="table mt-2 mb-0">
                <tr>
                    <td>Mean</td>
                    <td class="text-right">
                        {{ to2Dec(submissionStats.mean) }}
                    </td>
                </tr>
                <tr>
                    <td>Std. deviation</td>
                    <td class="text-right">
                        {{ to2Dec(submissionStats.stdev) }}
                    </td>
                </tr>
                <tr>
                    <td>Median</td>
                    <td class="text-right">
                        {{ to2Dec(submissionStats.median) }}
                    </td>
                </tr>
                <tr>
                    <td>Mode</td>
                    <td class="text-right">
                        {{ to2Dec(submissionStats.mode) }}
                    </td>
                </tr>
            </table>
        </description-popover>
    </div>

    <div class="border-right metric">
        <component :is="metricTag" class="d-block">
            <span v-if="feedbackStats == null">
                -
            </span>

            <span v-else class="position-relative">
                {{ to1Dec(feedbackStats.mean) }}

                <span class="extra text-muted">
                    &pm;{{ to1Dec(feedbackStats.stdev) }}
                </span>
            </span>
        </component>

        <label v-if="large">Average inline feedback entries</label>
        <label v-else>Avg. feedback</label>

        <description-popover v-if="large"
                             triggers="hover"
                             placement="top">
            The average number of inline feedback entries over the latest submissions.

            <table v-if="feedbackStats != null"
                   class="table mt-2 mb-0">
                <tr>
                    <td>Mean</td>
                    <td class="text-right">
                        {{ to2Dec(feedbackStats.mean) }}
                    </td>
                </tr>
                <tr>
                    <td>Std. deviation</td>
                    <td class="text-right">
                        {{ to2Dec(feedbackStats.stdev) }}
                    </td>
                </tr>
                <tr>
                    <td>Median</td>
                    <td class="text-right">
                        {{ to2Dec(feedbackStats.median) }}
                    </td>
                </tr>
                <tr>
                    <td>Mode</td>
                    <td class="text-right">
                        {{ to2Dec(feedbackStats.mode) }}
                    </td>
                </tr>
            </table>
        </description-popover>
    </div>
</b-card>
</template>

<script>
import DescriptionPopover from '@/components/DescriptionPopover';
import { Workspace, WorkspaceFilterResult } from '@/models/analytics';

export default {
    name: 'analytics-general-stats',

    props: {
        baseWorkspace: {
            type: [Workspace, WorkspaceFilterResult],
            required: true,
        },
        gradeWorkspace: {
            type: [Workspace, WorkspaceFilterResult],
            default: null,
        },
        feedbackWorkspace: {
            type: [Workspace, WorkspaceFilterResult],
            default: null,
        },
        large: {
            type: Boolean,
            default: false,
        },
    },

    data() {
        return {};
    },

    computed: {
        assignment() {
            return this.baseWorkspace.assignment;
        },

        studentType() {
            return this.assignment.group_set == null ? 'student' : 'group';
        },

        cardBodyClass() {
            let cls = 'd-flex flex-row flex-wrap px-0 pb-0';
            if (!this.large) {
                cls += ' p-1';
            }
            return cls;
        },

        metricTag() {
            return this.large ? 'h1' : 'b';
        },

        labelTag() {
            return this.large ? 'span' : 'small';
        },

        studentCount() {
            return this.baseWorkspace.submissions.studentCount;
        },

        submissionCount() {
            return this.baseWorkspace.submissions.submissionCount;
        },

        gradeStats() {
            const workspace = this.gradeWorkspace || this.baseWorkspace;
            return workspace.submissions.gradeStats;
        },

        submissionStats() {
            return this.baseWorkspace.submissions.submissionStats;
        },

        feedbackStats() {
            const workspace = this.feedbackWorkspace || this.baseWorkspace;
            const source = workspace.getSource('inline_feedback');
            return this.$utils.getProps(source, null, 'entryStats');
        },
    },

    methods: {
        to1Dec(x) {
            return this.$utils.toMaxNDecimals(x, 1);
        },

        to2Dec(x) {
            return this.$utils.toMaxNDecimals(x, 2);
        },
    },

    components: {
        DescriptionPopover,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.metric {
    flex: 0 0 auto;
    position: relative;
    text-align: center;

    .large & {
        margin-bottom: 1rem;
    }

    @media @media-no-medium {
        flex-basis: 50%;

        &:nth-child(2n) {
            border-right: 0 !important;
        }
    }

    @media @media-medium {
        flex-basis: 33.33%;

        &:nth-child(3n) {
            border-right-width: 0 !important;
        }
    }

    @media @media-large {
        flex-basis: 20%;

        &:nth-child(3n) {
            border-right-width: 1px !important;
        }

        &:nth-child(5n) {
            border-right: 0 !important;
        }
    }

    label {
        margin-bottom: 0;
    }

    .extra {
        position: absolute;
        left: calc(100% + 0.25em);
    }

    .analytics-general-stats.large & {
        label {
            padding: 0 1rem;
        }

        .extra {
            font-size: 50%;
            bottom: 0.66rem;
        }
    }

    .analytics-general-stats:not(.large) & {
        line-height: 1.1;

        label {
            font-size: small;
        }

        .extra {
            font-size: 75%;
            bottom: 0.25rem;
        }
    }

    .description-popover {
        position: absolute;
        top: 0;
        right: 0.5rem;
    }
}
</style>
