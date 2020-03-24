<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="feedback-area ">
    <div class="replies-wrapper pb-2">
        <transition-group name="fade"
                          tag="div">
            <div :key="reply.trackingId"
                 class="reply-wrapper"
                 v-if="!reply.deleted"
                 @click="() => unCollapse(reply)"
                 :class="{ collapsed: isCollapsed(reply), editing: isEditing(reply) }"
                 v-for="reply in replies">
                <div v-if="!isFirstNonDeletedReply(reply)"
                     @click.stop="toggleCollapse(reply)"
                     class="pr-1 reply-gutter">
                    <icon name="reply" class="reply-icon" />
                </div>
                <feedback-reply
                    @editing="(event) => onEditingEvent(reply, event)"
                    :is-collapsed="isCollapsed(reply)"
                    class="d-block"
                    :can-use-snippets="canUseSnippets"
                    :reply="reply"
                    :feedback-line="feedback"
                    :force-snippets-above="false"
                    :total-amount-lines="10000"
                    @updated="replyUpdated"
                    @deleted="replyDeleted"
                    :submission="submission" />
            </div>
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

// @ts-ignore
import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/reply';

import { FeedbackLine, FeedbackReply as FeedbackReplyModel } from '@/models/feedback';

import { Assignment } from '@/models/assignment';
// @ts-ignore
import { Submission } from '@/models/submission';

import FeedbackReply from './FeedbackReply';

@Component({
    components: {
        FeedbackReply,
        Icon,
    },
})
export default class FeedbackArea extends Vue {
    @Getter('user/id') myUserId!: number;

    @Action('feedback/addFeedbackLine') addFeedbackLine!: any;

    @Prop({ required: true }) feedback!: FeedbackLine;

    @Prop({ required: true }) canUseSnippets!: boolean;

    @Prop({ required: true }) submission!: Submission;

    collapsedReplies: Record<string, boolean> = {};

    editingReplies: Record<string, boolean> = {};

    get nonDeletedReplies(): FeedbackReplyModel[] {
        return this.feedback.replies.filter(r => !r.deleted);
    }

    isFirstNonDeletedReply(r: FeedbackReplyModel): boolean {
        const replies = this.nonDeletedReplies;
        return !r.deleted && replies.length > 0 && replies[0].trackingId === r.trackingId;
    }

    get showReply(): boolean {
        const replies = this.nonDeletedReplies;
        return (
            FeedbackLine.canAddReply(this.submission) &&
            replies.length > 0 && !replies[replies.length - 1].isEmpty
        );
    }

    get assignment(): Assignment {
        return this.submission.assignment;
    }

    get replies(): ReadonlyArray<FeedbackReplyModel> {
        return this.feedback.replies;
    }

    unCollapse(reply: FeedbackReplyModel): void {
        this.$delete(this.collapsedReplies, reply.trackingId);
    }

    toggleCollapse(reply: FeedbackReplyModel): void {
        const key = reply.trackingId;
        if (this.collapsedReplies[key]) {
            this.$delete(this.collapsedReplies, key);
        } else {
            this.$set(this.collapsedReplies, key, true);
        }
    }

    isCollapsed(reply: FeedbackReplyModel): boolean {
        return this.collapsedReplies[reply.trackingId] || false;
    }

    isEditing(reply: FeedbackReplyModel): boolean {
        return this.editingReplies[reply.trackingId] || false;
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

    onEditingEvent(reply: FeedbackReplyModel, event: any): void {
        this.$set(this.editingReplies, reply.trackingId, event.isEditing);
    }
}
</script>

<style lang="less" scoped>
@import '~mixins.less';

.reply-wrapper {
    transition: margin @transition-duration;
    margin-top: 1rem;

    &:not(:last-child) {
        margin-bottom: 1rem;
    }

    &:first-child {
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
    }

    &.collapsed {
        cursor: pointer;
        margin-top: 0;

        &:not(:last-child) {
            margin-bottom: 0.5rem;
        }
    }

    .reply-gutter {
        cursor: pointer;
    }

    &.editing .reply-gutter {
        cursor: unset;
        opacity: 0;
    }
}

.add-reply {
    cursor: text;
}

.fade-enter-active,
.fade-leave-active {
    transition: opacity @transition-duration;
}
.fade-enter,
.fade-leave-to {
    opacity: 0;
}

.reply-wrapper {
    display: flex;
    flex-direction: row;

    .feedback-reply {
        flex: 1 1 auto;
    }
}

.reply-icon {
    transform: rotate(180deg);

}
</style>
