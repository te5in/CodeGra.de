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

    <div class="metric"
         :class="{ 'border-right': $root.$isMediumWindow }">
        <component :is="metricTag" class="d-block">
            {{ submissionCount }}
        </component>

        <label>Submissions</label>
    </div>

    <hr v-if="!$root.$isMediumWindow"
        class="w-100 mt-0 mx-3"/>

    <div class="border-right metric">
        <component :is="metricTag"
                    class="d-block">

            <span v-if="averageGrade == null">
                -
            </span>

            <span v-else class="position-relative">
                {{ to2Dec(averageGrade.avg) }}

                <span class="extra text-muted">
                    &pm;{{ to1Dec(averageGrade.stdev) }}
                </span>
            </span>
        </component>

        <label v-if="large">Average grade</label>
        <label v-else>Avg. grade</label>

        <description-popover v-if="large"
                             triggers="hover"
                             placement="top">
            The average grade over the latest submissions.

            <template v-if="averageGrade != null">
                The standard deviation over the sample is {{ to1Dec(averageGrade.stdev) }}.
            </template>
        </description-popover>
    </div>

    <div class="metric"
         :class="{ 'border-right': $root.$isMediumWindow }">
        <component :is="metricTag" class="d-block">
            <span v-if="averageSubmissions == null">
                -
            </span>

            <span v-else class="position-relative">
                {{ to2Dec(averageSubmissions.avg) }}

                <span class="extra text-muted">
                    &pm;{{ to1Dec(averageSubmissions.stdev) }}
                </span>
            </span>
        </component>

        <label v-if="large">Average submissions</label>
        <label v-else>Avg. subs.</label>

        <description-popover v-if="large"
                             triggers="hover"
                             placement="top">
            The average number of submissions per {{ studentType }}.

            <template v-if="averageSubmissions != null">
                The standard deviation over the sample is {{ to1Dec(averageSubmissions.stdev) }}.
            </template>
        </description-popover>
    </div>

    <hr v-if="!$root.$isMediumWindow"
        class="w-100 mt-0 mx-3"/>

    <div class="metric">
        <component :is="metricTag" class="d-block">
            <span v-if="averageFeedbackEntries == null">
                -
            </span>

            <span v-else class="position-relative">
                {{ to2Dec(averageFeedbackEntries.avg) }}

                <span class="extra text-muted">
                    &pm;{{ to1Dec(averageFeedbackEntries.stdev) }}
                </span>
            </span>
        </component>

        <label v-if="large">Average inline feedback entries</label>
        <label v-else>Avg. feedback</label>

        <description-popover v-if="large"
                             triggers="hover"
                             placement="top">
            The average number of inline feedback entries over the latest submissions.

            <template v-if="averageFeedbackEntries != null">
                {{ to1Dec(averageFeedbackEntries.stdev) }}
            </template>
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
            let cls = 'd-flex flex-row flex-wrap pb-0';
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

        averageGrade() {
            const workspace = this.gradeWorkspace || this.baseWorkspace;
            return workspace.submissions.averageGrade;
        },

        averageSubmissions() {
            return this.baseWorkspace.submissions.averageSubmissions;
        },

        averageFeedbackEntries() {
            const workspace = this.feedbackWorkspace || this.baseWorkspace;
            const source = workspace.getSource('inline_feedback');
            return this.$utils.getProps(source, null, 'averageEntries');
        },
    },

    watch: {},

    methods: {
        to1Dec(x) {
            return this.$utils.toMaxNDecimals(x, 1);
        },

        to2Dec(x) {
            return this.$utils.toMaxNDecimals(x, 2);
        },
    },

    mounted() {},

    destroyed() {},

    components: {
        DescriptionPopover,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.metric {
    flex: 0 0 20%;
    position: relative;
    text-align: center;

    .large & {
        margin-bottom: 1rem;
    }

    @media @media-no-medium {
        flex-basis: 50%;
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
            font-size: 60%;
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
