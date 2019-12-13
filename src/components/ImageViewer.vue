<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<floating-feedback-button
    :disabled="!showInlineFeedback"
    v-if="imgURL"
    class="image-viewer"
    :fileId="id"
    :line="line"
    :feedback="feedback"
    :assignment="assignment"
    :submission="submission"
    :editable="editable"
    :can-use-snippets="canUseSnippets"
    slot-description="image"
    snippet-field-above
    always-show-button
    add-space>
    <img :src="imgURL"
         class="img"
         :title="name"
         @load="imgLoaded"/>
</floating-feedback-button>
</template>

<script>
import { mapActions } from 'vuex';
import FloatingFeedbackButton from './FloatingFeedbackButton';

export default {
    name: 'image-viewer',

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
        canUseSnippets: {
            type: Boolean,
            required: true,
        },
        revision: {
            type: String,
            required: true,
        },
        showInlineFeedback: {
            type: Boolean,
            default: true,
        },
    },

    data() {
        return {
            imgURL: '',
        };
    },

    watch: {
        id: {
            immediate: true,
            handler() {
                this.embedImg();
            },
        },

        name() {
            this.embedImg();
        },
    },

    computed: {
        id() {
            return this.file && (this.file.id || this.file.ids[0] || this.file.ids[1]);
        },

        name() {
            return this.file ? this.file.name : '';
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
                this.id,
                this.line,
            );
        },
    },

    methods: {
        ...mapActions('code', {
            storeLoadCode: 'loadCode',
        }),

        async embedImg() {
            this.imgURL = '';
            await this.$afterRerender();

            if (this.revision === 'diff') {
                this.$emit('error', 'The image viewer is not available in diff mode');
                return;
            }

            this.storeLoadCode(this.id).then(
                buffer => {
                    const blob = new Blob([buffer], { type: this.getMimeType() });
                    this.imgURL = URL.createObjectURL(blob);
                    // The image viewer itself emits a loaded event.
                },
                err => {
                    this.$emit(
                        'error',
                        `An error occured while loading the image: ${this.$utils.getErrorMessage(
                            err,
                        )}.`,
                    );
                },
            );
        },

        getMimeType() {
            const ext = this.name.split('.').reverse()[0];
            const types = {
                gif: 'image/gif',
                jpg: 'image/jpeg',
                jpeg: 'image/jpeg',
                png: 'image/png',
                svg: 'image/svg%2Bxml',
            };
            return types[ext];
        },

        imgLoaded() {
            this.$emit('load');
        },
    },

    components: {
        FloatingFeedbackButton,
    },
};
</script>

<style lang="less" scoped>
.image-viewer {
    padding: 0;
    overflow: auto !important;

    .img {
        display: block;
        max-width: 100%;
        max-height: 100%;
        flex: 1 1 auto;
        object-fit: contain;
    }
}
</style>

<style lang="less">
.image-viewer.floating-feedback-button .content {
    display: flex;
    flex-direction: column;
    align-items: center;
    min-height: 10rem;
}
</style>
