<template>
<div class="file-viewer"
     :class="dynamicClasses">
    <b-alert v-if="showError"
             show
             variant="danger"
             class="error mb-0">
        <template v-if="(fileData && showDiff(file) && !fileData.supportsDiff)">
            The diff for files of this type is not supported.
        </template>
        <template v-else>
            {{ error }}
        </template>
    </b-alert>

    <loader v-else-if="!dataAvailable"
            page-loader />

    <b-alert v-else-if="forcedFileComponent != null"
             show
             dismissible
             variant="warning"
             class="mb-0 border-bottom rounded-bottom-0">
        You are viewing the source of a file that can be rendered.
        <a href="#" @click.capture.prevent.stop="forcedFileComponent = null">Click here</a>
        to show the rendered version.
    </b-alert>

    <div class="wrapper"
         :class="{ scroller: fileData && fileData.scroller }"
         v-if="!showError">
        <div v-if="showEmptyFileMessage"
             class="wrapper px-3 py-1 text-muted">
            <small>This file is empty.</small>
        </div>
        <template v-else-if="fileData">
            <component v-show="dataAvailable"
                       :is="fileData.component"
                       class="inner-viewer"
                       :assignment="assignment"
                       :submission="submission"
                       :file="file"
                       :file-id="fileId"
                       :file-content="fileContent"
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
        </template>
    </div>
</div>
</template>

<script>
import { mapActions } from 'vuex';

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
            fileContent: undefined,
            fileTypes: [
                {
                    cond: () =>
                        UserConfig.features.render_html &&
                        this.hasExtension('html', 'htm') &&
                        this.revision !== 'diff',
                    component: HtmlViewer,
                    showLanguage: false,
                    scroller: false,
                },
                {
                    cond: () => this.hasExtension('pdf'),
                    component: PdfViewer,
                    showLanguage: false,
                    scroller: false,
                    needsContent: !this.$root.isEdge,
                },
                {
                    cond: () => this.hasExtension('gif', 'jpg', 'jpeg', 'png', 'svg'),
                    component: ImageViewer,
                    showLanguage: false,
                    scroller: false,
                    needsContent: true,
                },
                {
                    cond: () => this.hasExtension('ipynb'),
                    component: IpythonViewer,
                    showLanguage: false,
                    scroller: true,
                    needsContent: true,
                },
                {
                    cond: this.showDiff,
                    component: DiffViewer,
                    showLanguage: false,
                    scroller: true,
                    needsContent: false,
                    supportsDiff: true,
                },
                {
                    cond: () => this.hasExtension('md', 'markdown'),
                    component: MarkdownViewer,
                    showLanguage: false,
                    scroller: false,
                    needsContent: true,
                },
                {
                    cond: () => true,
                    component: CodeViewer,
                    showLanguage: true,
                    scroller: true,
                    needsContent: true,
                },
            ],
        };
    },

    computed: {
        showEmptyFileMessage() {
            return (
                !this.loading &&
                this.fileData &&
                this.fileContent &&
                this.fileContent.byteLength === 0
            );
        },

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
            if (this.showEmptyFileMessage) {
                return 'empty-file-wrapper form-control';
            } else if (this.fileData) {
                return `${this.fileData.component.name} border rounded ${
                    this.fileContent ? '' : 'no-data'
                }`;
            } else {
                return '';
            }
        },

        fileId() {
            let id = null;
            if (this.file) {
                id = this.file.id;
                if (this.file.ids) {
                    id = this.file.ids.find(x => x);
                }
            }

            return this.$utils.coerceToString(id);
        },

        dataAvailable() {
            return (
                this.fileData &&
                !this.loading &&
                (this.fileContent != null || !this.fileData.needsContent)
            );
        },

        showError() {
            return (
                this.error ||
                (this.fileData && this.showDiff(this.file) && !this.fileData.supportsDiff)
            );
        },
    },

    watch: {
        fileId: {
            immediate: true,
            async handler(newVal, oldVal) {
                if (!newVal || oldVal === newVal) {
                    return;
                }

                this.forcedFileComponent = null;
                // Do not throw an error while the submission page is loading, i.e. the fileId
                // has not been set yet.
                if (!this.file && this.$route.params.fileId) {
                    this.onError('File not found!');
                    return;
                }

                this.fileContent = null;
                this.error = '';
                this.loading = true;
                if (this.fileData.needsContent) {
                    let callback = () => {};
                    let content = null;

                    try {
                        [content] = await Promise.all([
                            this.storeLoadCode(newVal),
                            this.$afterRerender(),
                        ]);
                        if (content.byteLength === 0) {
                            callback = () => this.onLoad(newVal);
                        }
                    } catch (e) {
                        callback = () =>
                            this.onError({
                                error: e,
                                fileId: newVal,
                            });
                    }

                    if (newVal === this.fileId) {
                        if (content) {
                            this.fileContent = content;
                        }
                        callback();
                    }
                }
            },
        },
    },

    methods: {
        ...mapActions('code', {
            storeLoadCode: 'loadCode',
        }),

        onLoad(fileId) {
            if (this.fileId !== fileId) {
                return;
            }
            this.loading = false;
            this.error = '';
        },

        onError(err) {
            if (err.fileId) {
                if (err.fileId !== this.fileId) {
                    return;
                }
                this.error = this.$utils.getErrorMessage(err.error);
            } else {
                this.error = this.$utils.getErrorMessage(err);
            }
            this.loading = false;
        },

        async setForcedFileComponent(fc) {
            this.loading = true;
            this.error = '';
            await this.$afterRerender();
            this.forcedFileComponent = fc;
        },

        hasExtension(...exts) {
            return exts.some(
                ext => this.fileExtension === ext || this.fileExtension === ext.toUpperCase(),
            );
        },

        showDiff(file) {
            return this.revision === 'diff' && file.ids && file.ids[0] !== file.ids[1];
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

    &.html-viewer:not(.no-data) {
        height: 100%;
    }
    &.pdf-viewer:not(.no-data) {
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
