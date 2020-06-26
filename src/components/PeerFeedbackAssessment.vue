<template>
<div class="peer-feedback-assessment w-40">
    <table>
        <tbody>
            <tr>
                <td>
                    <div class="d-flex justify-content-between">
                        <label>Peer feedback score</label>
                        <promise-loader :promise="scorePromise"
                                        class="ml-3"
                                        @success="afterScoreUpdate"
                                        @after-error="scoreUpdateError" />
                    </div>
                </td>
                <td>
                    <b-form-group class="peer-feedback-score-group mx-5">
                        <b-form-radio-group :checked="score"
                                            @input="updateScore"
                                            buttons>
                            <b-form-radio :value="-1">
                                <fa-icon name="thumbs-down" />
                            </b-form-radio>
                            <b-form-radio :value="0">
                                <fa-icon name="meh-o" />
                            </b-form-radio>
                            <b-form-radio :value="1">
                                <fa-icon name="thumbs-up" />
                            </b-form-radio>
                        </b-form-radio-group>
                    </b-form-group>
                </td>
            </tr>
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
                               label-off="No"
                               class="mb-2"/>
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

    score: number | null = (this.reply.peerFeedback?.score ?? null);

    scorePromise: null | Promise<unknown> = null;

    get approved(): boolean {
        return this.reply.approved;
    }

    approvedPromise: null | Promise<unknown> = null;

    updateScore(score: number) {
        this.scorePromise = this.reply.updateScoreAndSave(score);
    }

    afterScoreUpdate(response: SubmitButtonResult<models.FeedbackReply>) {
        this.$emit('updated', response.cgResult);
        this.scorePromise = null;
    }

    scoreUpdateError() {
        this.score = this.reply.peerFeedback?.score ?? null;
        this.scorePromise = null;
    }

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

<style lang="less">
@import '~mixins.less';

.peer-feedback-assessment .peer-feedback-score-group .btn.active {
    text-decoration: underline !important;
    background-color: @color-primary !important;
    border-color: @color-primary !important;
    color: white !important;

    @{dark-mode} {
        background-color: @color-primary-darker;
        border-color: @color-primary-darker;
    }
}
</style>
