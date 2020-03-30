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

        <label>Students</label>
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
        <component :is="metricTag" class="d-block">
            {{ averageGrade }}
        </component>

        <label v-if="large">Average grade</label>
        <label v-else>Avg. grade</label>

        <description-popover v-if="large"
                             triggers="hover"
                             placement="top">
            The average grade over the latest submissions.
        </description-popover>
    </div>

    <div class="metric"
         :class="{ 'border-right': $root.$isMediumWindow }">
        <component :is="metricTag" class="d-block">
            {{ averageSubmissions }}
        </component>

        <label v-if="large">Average number of submissions</label>
        <label v-else>Avg. subs.</label>

        <description-popover v-if="large"
                             triggers="hover"
                             placement="top">
            The average number of submissions per student.
        </description-popover>
    </div>

    <hr v-if="!$root.$isMediumWindow"
        class="w-100 mt-0 mx-3"/>

    <div class="metric">
        <component :is="metricTag" class="d-block">
            {{ averageFeedbackEntries }}
        </component>

        <label v-if="large">Average number of feedback entries</label>
        <label v-else>Avg. feedback</label>

        <description-popover v-if="large"
                             triggers="hover"
                             placement="top">
            The average number of feedback entries over the latest submissions.
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
            const avg = workspace.submissions.averageGrade;
            return avg == null ? '-' : this.to2Dec(avg);
        },

        averageSubmissions() {
            const avg = this.baseWorkspace.submissions.averageSubmissions;
            return avg == null ? '-' : this.to2Dec(avg);
        },

        averageFeedbackEntries() {
            const workspace = this.feedbackWorkspace || this.baseWorkspace;
            const source = workspace.getSource('inline_feedback');
            const avg = this.$utils.getProps(source, null, 'averageEntries');
            return avg == null ? '-' : this.to2Dec(avg);
        },
    },

    watch: {},

    methods: {
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

    .analytics-general-stats.large & {
        label {
            padding: 0 1rem;
        }
    }

    .analytics-general-stats:not(.large) & {
        line-height: 1.1;

        label {
            font-size: small;
        }
    }

    .description-popover {
        position: absolute;
        top: 0;
        right: 0.5rem;
    }
}
</style>
