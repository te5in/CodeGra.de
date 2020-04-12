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
                :course="course"
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

    <div class="d-flex"
         :class="`justify-content-${noCancel ? 'end' : 'between'}`">
        <cg-submit-button
            v-if="!noCancel"
            variant="outline-danger"
            confirm="Are you sure you want to discard this email?"
            :submit="() => ({})"
            @success="$emit('hide')">
            Cancel
        </cg-submit-button>

        <cg-submit-button
            ref="submitButton"
            :submit="sendEmail"
            confirm="Are you sure you want to send this email?"
            @after-success="$emit('emailed')"
            label="Send">
            <template slot="error" slot-scope="e">
                <div v-if="$utils.getProps(e, null, 'error', 'response', 'data', 'code') === 'MAILING_FAILED'"
                      class="text-left">
                    Failed to email some users:

                    <ul>
                        <li v-for="user in e.error.response.data.failed_users">
                            <cg-user :user="user"  />
                        </li>
                    </ul>

                    <template v-if="getSuccessfulUsers(e.error.response.data).length > 0">
                        Please note that emailing these users did succeed:

                        <ul>
                            <li v-for="user in getSuccessfulUsers(e.error.response.data)">
                                <cg-user :user="user" />
                            </li>
                        </ul>
                    </template>

                </div>
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

import { SubmitButtonResult, Snippet } from '@/interfaces';
import * as models from '@/models';

// @ts-ignore
import SnippetableInput from './SnippetableInput';

@Component({
    components: {
        SnippetableInput,
    },
})
export default class StudentContact extends Vue {
    @Prop({ required: true }) submit!: (subject: string, body: string) =>
        Promise<SubmitButtonResult<models.TaskResult>>;

    @Prop({ required: true }) canUseSnippets!: boolean;

    @Prop({ required: true }) defaultSubject!: string;

    @Prop({ required: true }) course!: { snippets: Snippet[] | null };

    @Prop({ default: false }) noCancel!: boolean;

    public subject: string = this.defaultSubject;

    public body: string = '';

    public onDestroyHook = () => { };

    destroyed() {
        this.onDestroyHook();
    }

    @Ref() submitButton!: any;

    public sendEmail(): Promise<unknown> {
        if (!this.subject || !this.body) {
            throw new Error('Both the body and the subject should not be empty');
        }
        let destroyed = false;
        this.onDestroyHook = () => {
            destroyed = true;
        };

        return this.submit(this.subject, this.body).then(({ cgResult: taskResult }) => {
            if (destroyed) {
                return Promise.resolve();
            }
            const { promise, stop } = taskResult.poll();

            this.onDestroyHook = stop;
            return promise;
        });
    }

    // eslint-disable-next-line class-methods-use-this
    getSuccessfulUsers(data: {
        // eslint-disable-next-line camelcase
        all_users: models.UserServerData[], failed_users: models.UserServerData[]
    }): models.User[] {
        const failed = new Set(data.failed_users.map(x => x.id));
        return data.all_users.filter(u => !failed.has(u.id)).map(u => models.makeUser(u));
    }
}
</script>

<style lang="less" scoped>
ul {
    padding-left: 1rem;
}
</style>
