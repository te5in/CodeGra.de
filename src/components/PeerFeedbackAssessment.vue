<template>
<div class="peer-feedback-assessment">
    <promise-loader :promise="approvedPromise"
                    class="mr-2"
                    :scale="0.75"
                    @success="afterApproval"
                    @after-error="approvalError" />
    <span v-b-popover.top.hover="popoverMessage">
        <cg-toggle :value="approved"
                   @input="updateApproval"
                   :disabled="disabled || approvedPromise != null"
                   :has-no-value="approvedPromise != null"
                   class="d-inline-block">
            <template #label-off>
                <fa-icon :name="approved ? 'thumbs-o-down' : 'thumbs-down'"
                         class="text-danger" />
            </template>
            <template #label-on>
                <fa-icon :name="approved ? 'thumbs-up' : 'thumbs-o-up'"
                         class="text-success" />
            </template>
        </cg-toggle>
    </span>
</div>
</template>

<script lang="ts">
import { Vue, Component, Prop } from 'vue-property-decorator';
import 'vue-awesome/icons/thumbs-up';
import 'vue-awesome/icons/thumbs-o-up';
import 'vue-awesome/icons/thumbs-down';
import 'vue-awesome/icons/thumbs-o-down';

import { SubmitButtonResult } from '@/interfaces';
import * as models from '@/models';

import PromiseLoader from './PromiseLoader';

@Component({ components: { PromiseLoader } })
export default class PeerFeedbackAssessment extends Vue {
    @Prop({ required: true }) reply!: models.FeedbackReply;

    @Prop({ default: false }) disabled!: boolean;

    get approved(): boolean {
        return this.reply.approved;
    }

    get popoverMessage(): string {
        const comment = `${this.reply.isPeerFeedback ? 'peer feedback ' : ''}comment`;
        if (this.disabled) {
            return `This ${comment} has${this.approved ? '' : ' not'} been approved.`;
        }
        return `Change approval status for this ${comment}.`;
    }

    approvedPromise: null | Promise<unknown> = null;

    updateApproval(approved: boolean): Promise<unknown> {
        if (this.disabled) {
            return Promise.resolve();
        }
        this.approvedPromise = this.reply.approveAndSave(approved);
        return this.approvedPromise;
    }

    afterApproval(response: SubmitButtonResult<models.FeedbackReply>) {
        this.$emit('updated', response.cgResult);
        this.approvedPromise = null;
    }

    approvalError() {
        this.approvedPromise = null;
    }
}
</script>

<style lang="less">
.peer-feedback-assessment .toggle {
    margin: 0 !important;
    transform: scale(0.75);
}
</style>
