<template>
<div class="file-viewer"
     :class="dynamicClasses">
    <b-alert class="error mb-0" variant="danger" show v-if="error">
        <div v-html="error"/>
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
                   :revision="revision"
                   :show-whitespace="showWhitespace"
                   :editable="editable"
                   @language="$emit('language', $event)"
                   :language="language"
                   :can-use-snippets="canUseSnippets"
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
            fileTypes: [
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
                    cond: f => this.revision === 'diff' && f.ids[0] !== f.ids[1],
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
            return this.file ? this.fileTypes.find(ft => ft.cond(this.file)) : null;
        },

        dynamicClasses() {
            if (this.fileData) {
                return `${this.fileData.component.name} form-control`;
            } else {
                return '';
            }
        },
    },

    watch: {
        file: {
            handler(newVal, oldVal) {
                if (oldVal && newVal && oldVal.id === newVal.id) {
                    return;
                }

                // Do not throw an error while the submission page is loading, i.e. the fileId
                // has not been set yet.
                if (!this.file && this.$route.params.fileId) {
                    this.onError('File not found!');
                } else {
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

    &.pdf-viewer {
        height: 100%;
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
