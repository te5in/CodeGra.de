<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="feedback-area ">
    <div class="reply-wrapper pb-2">
        <transition-group name="fade"
                          tag="div">
            <feedback-reply
                class="d-block"
                :key="reply.trackingId"
                v-if="!reply.deleted"
                v-for="reply in replies"
                :editable="editable"
                :can-use-snippets="canUseSnippets"
                :reply="reply"
                :feedback-line="feedback"
                :force-snippets-above="false"
                :total-amount-lines="10000"
                @updated="replyUpdated"
                @deleted="replyDeleted"
                :submission="submission" />
        </transition-group>
    </div>
    <div @click.prevent="addReply"
         class="add-reply text-muted p-2 border rounded my-2 border-top"
         v-if="showReply">
        Reply&hellip;
    </div>
</div>
</template>

<script lang="ts">
    import { Vue, Component, Prop } from 'vue-property-decorator';
import { Getter, Action } from 'vuex-class';

import { FeedbackLine, FeedbackReply as FeedbackReplyModel } from '@/models/feedback';

import { Assignment } from '@/models/assignment';
// @ts-ignore
import { Submission } from '@/models/submission';

import FeedbackReply from './FeedbackReply';

@Component({
    components: {
        FeedbackReply,
    },
})
export default class FeedbackArea extends Vue {
    @Getter('user/id') myUserId!: number;

    @Action('feedback/addFeedbackLine') addFeedbackLine!: any;

    @Prop({ required: true }) feedback!: FeedbackLine;

    @Prop({ required: true }) editable!: boolean;

    @Prop({ required: true }) canUseSnippets!: boolean;

    @Prop({ required: true }) submission!: Submission;

    get nonDeletedReplies(): FeedbackReplyModel[] {
        return this.feedback.replies.filter(r => !r.deleted);
    }

    get showReply(): boolean {
        const replies = this.nonDeletedReplies;
        return replies.length > 0 && !replies[replies.length - 1].isEmpty;
    }

    get assignment(): Assignment {
        return this.submission.assignment;
    }

    get replies(): ReadonlyArray<FeedbackReplyModel> {
        return this.feedback.replies;
    }

    updateLine(newLine: FeedbackLine) {
        // Make sure we don't display that a comment was placed in the future.
        this.$root.$emit('cg::root::update-now');
        this.addFeedbackLine({
            assignmentId: this.assignment.id,
            submissionId: (this.submission as any).id,
            fileId: this.feedback.fileId,
            line: newLine,
        });
    }

    replyUpdated(newReply: FeedbackReplyModel): void {
        const line = this.feedback.updateReply(newReply);
        this.updateLine(line);
    }

    replyDeleted(deletedReply: FeedbackReplyModel): void {
        this.updateLine(this.feedback.deleteReply(deletedReply));
    }

    addReply(): void {
        const line = this.feedback.addReply(
            FeedbackReplyModel.createEmpty(this.myUserId, this.feedback.id),
        );
        this.updateLine(line);
    }
}
</script>

<style lang="less" scoped>
@import '~mixins.less';

.feedback-reply:first-child {
    margin-top: 0.5rem;
}

.feedback-reply:not(:first-child) {
    margin-top: 1rem;
}

.add-reply {
    cursor: text;
    box-shadow: inset 0 1px 1px rgba(0,0,0,.075),0 0 8px rgba(102,175,233,.6);

}

.fade-enter-active,
.fade-leave-active {
    transition: opacity @transition-duration;
}
.fade-enter,
.fade-leave-to {
    opacity: 0;
}
</style>
