<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<floating-feedback-button
    class="markdown-viewer"
    :style="{ fontSize: `${fontSize}px`}"
    :fileId="fileId"
    :line="line"
    :feedback="feedback"
    :editable="editable"
    :can-use-snippets="canUseSnippets"
    :assignment="assignment"
    :submission="submission"
    slot-description="file"
    snippet-field-above
    always-show-button
    add-space>
    <inner-markdown-viewer v-if="data"
                           class="py-2 px-3"
                           :markdown="data"
                           :show-code-whitespace="showWhitespace"/>
</floating-feedback-button>
</template>

<script>
import { mapGetters, mapActions } from 'vuex';
import decodeBuffer from '@/utils/decode';

import InnerMarkdownViewer from './InnerMarkdownViewer';
import FloatingFeedbackButton from './FloatingFeedbackButton';
import Loader from './Loader';

export default {
    name: 'markdown-viewer',

    props: {
        assignment: {
            type: Object,
            required: true,
        },
        submission: {
            type: Object,
            required: true,
        },
        file: {
            type: Object,
            default: null,
        },
        editable: {
            type: Boolean,
            default: false,
        },
        showWhitespace: {
            type: Boolean,
            default: true,
        },
        canUseSnippets: {
            type: Boolean,
            required: true,
        },
    },

    data() {
        return {
            data: null,
        };
    },

    computed: {
        ...mapGetters('pref', ['fontSize']),

        fileId() {
            return this.file.id || this.file.ids[0] || this.file.ids[1];
        },

        line() {
            return 0;
        },

        feedback() {
            return this.$utils.getProps(
                this.submission,
                {},
                'feedback',
                'user',
                this.fileId,
                this.line,
            );
        },
    },

    methods: {
        ...mapActions('code', {
            storeLoadCode: 'loadCode',
        }),

        async loadCode() {
            this.data = '';
            await this.$afterRerender();

            try {
                this.data = decodeBuffer(await this.storeLoadCode(this.fileId));
                this.$emit('load');
            } catch (e) {
                this.$emit('error', e);
            }
        },
    },

    watch: {
        fileId: {
            immediate: true,
            handler() {
                this.loadCode();
            },
        },
    },

    components: {
        InnerMarkdownViewer,
        FloatingFeedbackButton,
        Loader,
    },
};
</script>
