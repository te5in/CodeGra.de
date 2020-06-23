<template>
<div class="junit-result">
    <div v-for="suite in junit.suites" class="junit-suite p-3">
        <h5>
            {{ suite.name }} ({{ suite.successful }} / {{ suite.runTests }})
        </h5>
        <masonry :cols="{ default: 2 }"
                 gutter="0.5rem">
            <div v-for="testCase in suite.cases" class="py-1">
                <div class="border rounded overflow-hidden">
                    <div class="d-flex flex-row p-2">
                        <div class="flex-grow-1">
                            <b-badge class="classname">
                                <code>{{ testCase.classname }}</code>
                            </b-badge>
                            {{ testCase.name }}
                        </div>

                        <div v-b-popover.top.hover="`This test finished with a ${testCase.state} state.`"
                             class="flex-grow-0 ml-2">
                            <fa-icon :name="testCase.fontAwesomeIcon.icon"
                                     style="width: 1rem;"
                                     :class="testCase.fontAwesomeIcon.cls" />
                        </div>
                    </div>

                    <div v-if="testCase.content != null">
                        <inner-code-viewer class="border-top"
                                           v-if="testCase.content"
                                           :assignment="assignment"
                                           :code-lines="testCase.content"
                                           file-id="-1"
                                           :feedback="{}"
                                           :start-line="0"
                                           :show-whitespace="true"
                                           :warn-no-newline="false"
                                           :empty-file-message="'No output.'" />
                    </div>
                </div>
            </div>
        </masonry>
    </div>
</div>
</template>

<script lang="ts">
import 'vue-awesome/icons/ban';
import 'vue-awesome/icons/check';
import 'vue-awesome/icons/times';
import 'vue-awesome/icons/exclamation';
import { Vue, Component, Prop } from 'vue-property-decorator';
import { CGJunit } from '@/utils/junit';
import { Assignment } from '@/models';

// @ts-ignore
import InnerCodeViewer from './InnerCodeViewer';

@Component({
    components: {
        InnerCodeViewer,
    },
})
export default class JunitResult extends Vue {
    @Prop({ required: true })
    junit!: CGJunit;

    @Prop({ required: true })
    assignment!: Assignment;
}
</script>

<style lang="less" scoped>
@import "~mixins.less";

.junit-suite:not(:last-child) {
    border-bottom: 1px solid @border-color;
}

.badge.classname {
    background: none !important;

    code {
        font-size: 100% !important;
    }
}

</style>
