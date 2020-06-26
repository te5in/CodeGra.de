<template>
<div class="peer-feedback-assessment w-40">
    <table>
        <tbody>
            <tr>
                <td>
                    <div class="d-flex justify-content-between">
                        Approved
                        <promise-loader :promise="approvedPromise"
                                        class="ml-3"
                                        @success="afterApproval"
                                        @after-error="approvalError" />
                    </div>
                </td>
                <td>
                    <cg-toggle :value="approved"
                               @input="updateApproval"
                               :disabled="approvedPromise != null"
                               :has-no-value="approvedPromise != null"
                               no-disabled-popover
                               label-on="Yes"
                               label-off="No"/>
                </td>
            </tr>
        </tbody>
    </table>
</div>
</template>

<script lang="ts">
import { Vue, Component, Prop } from 'vue-property-decorator';
import 'vue-awesome/icons/thumbs-up';
import 'vue-awesome/icons/thumbs-down';
import 'vue-awesome/icons/meh-o';

import { SubmitButtonResult } from '@/interfaces';
import * as models from '@/models';

import PromiseLoader from './PromiseLoader';

@Component({ components: { PromiseLoader } })
export default class PeerFeedbackAssessment extends Vue {
    @Prop({ required: true }) reply!: models.FeedbackReply;

    get approved(): boolean {
        return this.reply.approved;
    }

    approvedPromise: null | Promise<unknown> = null;

    updateApproval(approved: boolean) {
        this.approvedPromise = this.reply.approveAndSave(approved);
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
