<template>
<div class="file-viewer"
     :class="dynamicClasses">
    <b-alert class="error mb-0" variant="danger" show v-if="error">
        {{ error }}
    </b-alert>

    <loader v-else-if="loading"
            page-loader />

    <div class="wrapper" :class="{ scroller: fileData && fileData.scroller }">
        <component v-show="!loading"
                   v-if="fileData"
                   :is="fileData.component"
                   class="inner-viewer"
                   :assignment="assignment"
                   :submission="submission"
                   :file="file"
                   :file-id="fileId"
                   :revision="revision"
                   :show-whitespace="showWhitespace"
                   :show-inline-feedback="showInlineFeedback"
                   :editable="editable"
                   @language="$emit('language', $event)"
                   :language="language"
                   :can-use-snippets="canUseSnippets"
                   @force-viewer="setForcedFileComponent"
                   @load="onLoad"
                   @error="onError" />
    </div>
</div>
</template>

<script>
import {
    CodeViewer,
    DiffViewer,
    ImageViewer,
    IpythonViewer,
    MarkdownViewer,
    PdfViewer,
    HtmlViewer,
} from '@/components';

import Loader from './Loader';

export default {
    name: 'file-viewer',

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
        revision: {
            type: String,
            required: true,
        },
        editable: {
            type: Boolean,
            default: false,
        },
        showWhitespace: {
            type: Boolean,
            required: true,
        },
        showInlineFeedback: {
            type: Boolean,
            default: true,
        },
        language: {
            type: String,
            default: 'Default',
        },
        canUseSnippets: {
            type: Boolean,
            required: true,
        },
    },

    data() {
        return {
            loading: true,
            error: '',
            forcedFileComponent: null,
            fileTypes: [
                {
                    cond: f => f.name.endsWith('.html'),
                    component: HtmlViewer,
                    showLanguage: false,
                    scroller: false,
                },
                {
                    cond: () => this.fileExtension === 'pdf',
                    component: PdfViewer,
                    showLanguage: false,
                    scroller: false,
                },
                {
                    cond: () => /^(?:gif|jpe?g|png|svg)$/.test(this.fileExtension),
                    component: ImageViewer,
                    showLanguage: false,
                    scroller: false,
                },
                {
                    cond: f => f.ids && f.ids[0] !== f.ids[1],
                    component: DiffViewer,
                    showLanguage: false,
                    scroller: true,
                },
                {
                    cond: () => this.fileExtension === 'ipynb',
                    component: IpythonViewer,
                    showLanguage: false,
                    scroller: true,
                },
                {
                    cond: () => this.fileExtension === 'md' || this.fileExtension === 'markdown',
                    component: MarkdownViewer,
                    showLanguage: false,
                    scroller: false,
                },
                {
                    cond: () => !this.error,
                    component: CodeViewer,
                    showLanguage: true,
                    scroller: true,
                },
            ],
        };
    },

    computed: {
        fileExtension() {
            const parts = this.file.name.split('.');

            if (parts.length > 1) {
                return parts[parts.length - 1].toLowerCase();
            } else {
                return '';
            }
        },

        fileData() {
            // access file id to make sure this computed value changes when `fileId` changes.
            // eslint-disable-next-line
            const _ = this.fileId;

            if (!this.file) {
                return null;
            } else if (this.forcedFileComponent) {
                return this.fileTypes.find(ft => ft.component === this.forcedFileComponent);
            }
            return this.fileTypes.find(ft => ft.cond(this.file));
        },

        dynamicClasses() {
            if (this.fileData) {
                return `${this.fileData.component.name} form-control ${this.loading ? 'loading' : ''}`;
            } else {
                return '';
            }
        },

        fileId() {
            if (!this.file) {
                return null;
            } else {
                return String(this.file.id || this.file.ids[0] || this.file.ids[1]);
            }
        },
    },

    watch: {
        fileId: {
            handler(newVal, oldVal) {
                if (oldVal && newVal && oldVal === newVal) {
                    return;
                }

                this.forcedFileComponent = null;
                // Do not throw an error while the submission page is loading, i.e. the fileId
                // has not been set yet.
                if (!this.file && this.$route.params.fileId) {
                    this.onError('File not found!');
                } else {
                    this.error = '';
                    this.loading = true;
                }
            },
        },
    },

    methods: {
        onLoad() {
            this.loading = false;
            this.error = '';
        },

        onError(err) {
            this.error = this.$utils.getErrorMessage(err);
            this.loading = false;
        },

        async setForcedFileComponent(fc) {
            this.loading = true;
            this.error = '';
            await this.$afterRerender();
            this.forcedFileComponent = fc;
        },
    },

    components: {
        Loader,
    },
};
</script>

<style lang="less" scoped>
.file-viewer {
    overflow: hidden;
    padding: 0 !important;
    display: flex;
    flex-direction: column;

    &.html-viewer:not(.loading) {
        height: 100%;
    }
    &.pdf-viewer {
        height: 100%;
        flex: 1 1 100%;
    }
}

.wrapper {
    position: relative;
    flex: 1 1 auto;
    min-height: 0;
    max-height: 100%;
    width: 100%;
    overflow: hidden;

    &:not(.scroller) {
        display: flex;
        flex-direction: column;
    }
}

.scroller {
    // Fixes performance issues on scrolling because the entire
    // code viewer isn't repainted anymore.
    will-change: transform;

    overflow: auto;
}

.inner-viewer {
    min-height: 100%;
}

.loader {
    margin: 2rem 0;
}
</style>
