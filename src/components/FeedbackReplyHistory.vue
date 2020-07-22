<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="feedback-reply-history" :class="{ loading: loading }">
    <b-alert variant="error" show v-if="error != null">
        {{ $utils.getErrorMessage(errro) }}
    </b-alert>
    <cg-loader :scale="2" v-else-if="loading" class="p-3"/>
    <template v-else>
        <table class="table">
            <thead>
                <tr>
                    <th class="shrink">When</th>
                    <th class="shrink">Editor</th>
                    <th>Diff</th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="edit in edits">
                    <td><cg-relative-time :date="edit.createdAt" /></td>
                    <td><cg-user :user="edit.editor" /></td>
                    <td class="text-left diff-wrapper" v-html="edit.getDiffHtml()" />
                </tr>
            </tbody>
        </table>
    </template>
</div>
</template>

<script lang="ts">
import { Vue, Component, Prop, Watch } from 'vue-property-decorator';

import * as models from '@/models';

@Component
export default class FeedbackReply extends Vue {
    @Prop({ required: true }) reply!: models.FeedbackReply;

    edits: models.FeedbackReplyEdit[] | null = null;

    error: Error | null = null;

    loading: boolean = true;

    @Watch('reply')
    onReplyUpdate() {
        this.loadEdits();
    }

    created() {
        this.loadEdits();
    }

    async loadEdits(): Promise<void> {
        this.edits = null;
        this.error = null;
        this.loading = true;

        try {
            this.edits = (await this.reply.fetchEdits()).cgResult;
        } catch (e) {
            this.error = e;
        } finally {
            this.loading = false;
        }
    }
}
</script>

<style lang="less">
@import '~mixins.less';

.feedback-reply-history {
    &:not(.loading) {
        max-height: 20rem;
        overflow-y: auto;
    }

    .diff-wrapper {
        white-space: pre-wrap;
        .added {
            background-color: @color-diff-added-light !important;

            @{dark-mode} {
                background-color: @color-diff-added-dark !important;
            }
        }

        .removed {
            background-color: @color-diff-removed-light !important;

            @{dark-mode} {
                background-color: @color-diff-removed-dark !important;
            }
        }
    }

    .table {
        margin-bottom: 0;
        td {
            vertical-align: top;
        }
    }
}
</style>
