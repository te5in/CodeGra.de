<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<floating-feedback-button
    v-if="pdfURL"
    class="pdf-viewer"
    :fileId="id"
    :line="line"
    :feedback="feedback"
    :assignment="assignment"
    :submission="submission"
    :editable="editable"
    :can-use-snippets="canUseSnippets"
    slot-description="pdf"
    snippet-field-above
    always-show-button
    add-space>
    <object :data="pdfURL"
            type="application/pdf"
            width="100%"
            height="100%"
            v-if="pdfURL !== ''">
        <b-alert class="mb-0" variant="danger" show>
            Your browser doesn't support the PDF viewer. Please download
            the PDF <a class="alert-link" :href="pdfURL">here</a>.
        </b-alert>
    </object>
</floating-feedback-button>
</template>

<script>
import { mapActions } from 'vuex';

import FloatingFeedbackButton from './FloatingFeedbackButton';

export default {
    name: 'pdf-viewer',

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
            required: true,
        },
        revision: {
            type: String,
            required: true,
        },
        editable: {
            type: Boolean,
            required: false,
        },
        canUseSnippets: {
            type: Boolean,
            required: true,
        },
    },

    data() {
        return {
            pdfURL: '',
        };
    },

    watch: {
        id: {
            immediate: true,
            handler() {
                this.embedPdf();
            },
        },
    },

    computed: {
        id() {
            return this.file ? this.file.id : -1;
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

        async embedPdf() {
            this.pdfURL = '';
            await this.$afterRerender;

            if (this.revision === 'diff') {
                this.$emit('error', 'The pdf viewer is not available in diff mode');
                return;
            }

            let prom;
            if (this.$root.isEdge) {
                prom = this.$http.get(`/api/v1/code/${this.id}?type=file-url`).then(({ data }) => {
                    this.pdfURL = `/api/v1/files/${
                        data.name
                    }?not_as_attachment&mime=application/pdf`;
                });
            } else {
                prom = this.storeLoadCode(this.id).then(buffer => {
                    const blob = new Blob([buffer], { type: 'application/pdf' });
                    this.pdfURL = `${URL.createObjectURL(blob)}`;
                });
            }

            prom.then(
                () => {
                    this.$emit('load');
                },
                err => {
                    this.$emit(
                        'error',
                        `An error occured while loading the PDF: ${this.$utils.getErrorMessage(
                            err,
                        )}.`,
                    );
                },
            );
        },
    },

    components: {
        FloatingFeedbackButton,
    },
};
</script>

<style lang="less" scoped>
.pdf-viewer {
    position: relative;
    padding: 0 !important;
    height: 100%;
    min-height: 100%;
}

object {
    display: block;
    flex: 1 1 100%;
    width: 100%;
    height: 100%;
    margin: 0;
    padding: 0;
}
</style>

<style lang="less">
.pdf-viewer.floating-feedback-button {
    flex: 1 1 100%;

    > .content {
        display: flex;
        flex-direction: column;
    }
}
</style>
