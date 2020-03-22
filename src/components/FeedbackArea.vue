<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="feedback-area">
    <div v-for="reply in replies">
        {{ reply }} {{ reply.constructor.name }}
    </div>
</div>
</template>

<script lang="ts">
import { Vue, Component, Prop } from 'vue-property-decorator';

import { FeedbackLine, FeedbackReply } from '@/models/feedback';

import { Assignment } from '@/models/assignment';

// @ts-ignore
import { Submission } from '@/models/submission';

@Component
export default class FeedbackArea extends Vue {
    @Prop({ required: true })
    feedback!: FeedbackLine;

    @Prop({ required: true })
    editable!: boolean;

    @Prop({ required: true })
    line!: number;

    @Prop({ required: true })
    canUseSnippets!: boolean;

    @Prop({ required: true })
    submission!: Submission;

    get assignment(): Assignment {
        return this.submission.assignment;
    }

    get replies(): ReadonlyArray<FeedbackReply> {
        return this.feedback.replies;
    }
}
</script>

<style lang="less" scoped>

</style>
