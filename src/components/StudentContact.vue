<template>
<div class="student-contact p-relative">
    <div class="text-left" >
        <b-form-group>
            <label>Subject</label>
            <input v-model="subject" class="form-control" />
        </b-form-group>

        <b-form-group>
            <label>Body</label>
            <snippetable-input
                v-model="body"
                :assignment="submission.assignment"
                :force-snippets-above="false"
                :total-amount-lines="1000"
                :feedback-disabled="false"
                :can-use-snippets="canUseSnippets"
                :min-initial-height="300"
                :line="0"
                @ctrlEnter="() => submitButton.onClick()"
                :bounce-time="300" />
        </b-form-group>
    </div>

    <div class="d-flex justify-content-between">
        <cg-submit-button
            variant="outline-danger"
            confirm="Are you sure you want to discard this email?"
            :submit="() => ({})"
            @success="$emit('hide')">
            Cancel
        </cg-submit-button>

        <cg-submit-button
            ref="submitButton"
            :submit="sendEmail"
            confirm="Are you sure you want to send this email to all authors of this submission?"
            @after-success="$emit('hide')"
            label="Send">
            <template slot="error" slot-scope="e">
                <span v-if="$utils.getProps(e, null, 'error', 'response', 'data', 'code') === 'MAILING_FAILED'">
                    Failed to email some authors:

                    <ul>
                        <li v-for="user in e.error.response.data.failed_authors">
                            <cg-user :user="user"  />
                        </li>
                    </ul>
                </span>
                <span v-else>
                    {{ $utils.getErrorMessage(e.error) }}
                </span>
            </template>
        </cg-submit-button>
    </div>
</div>
</template>

<script lang="ts">

    import { Vue, Component, Prop, Ref } from 'vue-property-decorator';

import * as models from '@/models';

// @ts-ignore
import SnippetableInput from './SnippetableInput';

@Component({
    components: {
        SnippetableInput,
    },
})
export default class StudentContact extends Vue {
    @Prop({ required: true }) submission!: models.Submission;

    @Prop({ required: true }) canUseSnippets!: boolean;

    public subject: string = '';

    public body: string = '';

    @Ref() submitButton!: any;

    public sendEmail(): Promise<Object> {
        if (!this.subject || !this.body) {
            throw new Error('Both the body and the subject should not be empty');
        }

        return this.$http.post(`/api/v1/submissions/${this.submission.id}/email`, {
            subject: this.subject,
            body: this.body,
        });
    }
}
</script>

<style lang="less" scoped>
ul {
    padding-left: 1rem;
}
</style>
