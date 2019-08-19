<template>
<b-alert class="error" variant="danger" show v-if="error">
    <div v-html="error"/>
</b-alert>

<loader page-loader v-else-if="loading" />

<div v-else-if="!canSeeFeedback" class="p-3 border rounded font-italic text-muted">
    Feedback not yet available.
</div>

<div v-else class="feedback-overview border rounded">
    <div class="scroller">
        <b-card header="General feedback">
            <pre v-if="generalFeedback"
                 class="general-feedback mb-0">{{ generalFeedback }}</pre>
            <span v-else class="text-muted font-italic">
                No general feedback given.
            </span>
        </b-card>

        <b-card v-if="fileIds.length === 0"
                header="Inline feedback">
            <span class="text-muted font-italic">
                This submission has no line comments.
            </span>
        </b-card>

        <template v-else>
            <b-card v-for="id in fileIds"
                    :key="id">
                <router-link slot="header" :to="getFileLink(id)">
                    {{ fileTree.flattened[id] }}
                </router-link>

                <div v-if="disabledFileType(id)">
                    Overview mode is not available for {{ disabledFileType(id).name }}. Click
                    <router-link class="inline-link" :to="getFileLink(id)">here</router-link>
                    to see the entire file.

                    <feedback-area v-if="disabledFileType(id).singleLine"
                                   :line="0"
                                   :feedback="feedback.user[id][0].msg"
                                   :author="feedback.user[id][0].author"
                                   :assignment="assignment"
                                   :submission="submission" />
                </div>

                <div v-else
                     v-for="(part, i) in getParts(id)"
                     :key="`file-${id}-line-${part[0]}`">
                    <hr v-if="i !== 0">

                    <inner-code-viewer class="form-control"
                                       :assignment="assignment"
                                       :submission="submission"
                                       :code-lines="codeLines[id]"
                                       :feedback="feedback.user[id] || null"
                                       :linter-feedback="feedback.linter[id]"
                                       :editable="false"
                                       :file-id="0"
                                       :start-line="part[0]"
                                       :end-line="part[1]"
                                       :show-whitespace="showWhitespace"/>
                </div>
            </b-card>
        </template>
    </div>
</div>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';

import decodeBuffer from '@/utils/decode';

import Loader from './Loader';
import InnerCodeViewer from './InnerCodeViewer';
import FeedbackArea from './FeedbackArea';

export default {
    name: 'feedback-overview',

    props: {
        assignment: {
            type: Object,
            required: true,
        },
        submission: {
            type: Object,
            required: true,
        },
        showWhitespace: {
            type: Boolean,
            default: true,
        },
        canSeeFeedback: {
            type: Boolean,
            default: false,
        },
    },

    data() {
        return {
            error: '',
            codeLines: null,
        };
    },

    computed: {
        ...mapGetters('pref', ['contextAmount', 'fontSize']),
        ...mapGetters('courses', ['assignments']),

        loading() {
            const feedback = this.feedback;
            const fileTree = this.fileTree;
            const codeLines = this.codeLines;

            return feedback == null || fileTree == null || codeLines == null;
        },

        fileTree() {
            return this.submission.fileTree;
        },

        feedback() {
            const feedback = this.submission.feedback;

            if (!feedback || !this.canSeeFeedback) {
                return {};
            }

            return this.submission.feedback;
        },

        fileIds() {
            return Object.keys(this.$utils.getProps(this.feedback, {}, 'user'));
        },

        generalFeedback() {
            return this.submission.comment || '';
        },
    },

    watch: {
        submission: {
            immediate: true,
            handler() {
                this.loadFeedback();
            },
        },

        fileIds: {
            immediate: true,
            handler() {
                this.loadCode();
            },
        },
    },

    methods: {
        ...mapActions('courses', {
            storeLoadSubmissionFeedback: 'loadSubmissionFeedback',
            storeLoadSubmissionFileTree: 'loadSubmissionFileTree',
        }),

        async loadFeedback() {
            this.codeLines = null;
            this.error = '';

            Promise.all([
                this.storeLoadSubmissionFeedback({
                    assignmentId: this.assignment.id,
                    submissionId: this.submission.id,
                }),
                this.storeLoadSubmissionFileTree({
                    assignmentId: this.assignment.id,
                    submissionId: this.submission.id,
                }),
            ]).catch(err => {
                this.error = this.$utils.getErrorMessage(err);
            });
        },

        async loadCode() {
            if (this.fileIds == null) {
                return;
            }

            if (this.fileIds.length === 0) {
                this.codeLines = {};
                return;
            }

            const codeLines = await Promise.all(this.fileIds.map(this.loadCodeWithSettings));

            this.codeLines = this.fileIds.reduce((acc, id, i) => {
                acc[id] = codeLines[i];
                return acc;
            }, {});
        },

        async loadCodeWithSettings(fileId) {
            const val = await this.$hlanguageStore.getItem(`${fileId}`);
            let selectedLanguage;

            if (val !== null) {
                selectedLanguage = val;
            } else {
                selectedLanguage = 'Default';
            }
            return this.getCode(fileId, selectedLanguage);
        },

        getCode(fileId, selectedLanguage) {
            return this.$http
                .get(`/api/v1/code/${fileId}`, {
                    responseType: 'arraybuffer',
                })
                .then(
                    rawCode => {
                        let code;
                        try {
                            code = decodeBuffer(rawCode.data);
                        } catch (e) {
                            return [];
                        }
                        return this.highlightCode(
                            code.split('\n'),
                            selectedLanguage,
                            this.fileTree.flattened[fileId],
                        );
                    },
                    err => {
                        this.error = this.$utils.getErrorMessage(err);
                    },
                );
        },

        highlightCode(codeLines, language, filePath) {
            const lang = language === 'Default' ? this.$utils.getExtension(filePath) : language;
            return this.$utils.highlightCode(codeLines, lang, 1000);
        },

        getFileLink(fileId, revision) {
            const newQuery = Object.assign({}, this.$route.query, {
                revision,
            });

            return {
                name: 'submission_file',
                params: {
                    courseId: this.assignment.course.id,
                    assignmentId: this.assignment.id,
                    submissionId: this.submission.id,
                    fileId,
                },
                query: newQuery,
                hash: '#code',
            };
        },

        disabledFileType(fileId) {
            const file = this.fileTree.flattened[fileId];
            if (!file) {
                return false;
            }
            const parts = file.split('.');
            return {
                ipynb: {
                    name: 'IPython notebooks',
                    singleLine: false,
                },
                md: {
                    name: 'markdown files',
                    singleLine: true,
                },
                markdown: {
                    name: 'markdown files',
                    singleLine: true,
                },
                svg: {
                    name: 'images',
                    singleLine: true,
                },
                gif: {
                    name: 'images',
                    singleLine: true,
                },
                jpeg: {
                    name: 'images',
                    singleLine: true,
                },
                jpg: {
                    name: 'images',
                    singleLine: true,
                },
                png: {
                    name: 'images',
                    singleLine: true,
                },
                pdf: {
                    name: 'PDF files',
                    singleLine: true,
                },
            }[parts.length > 1 ? parts[parts.length - 1] : ''];
        },

        getParts(fileId) {
            const last = this.$utils.last;
            const lines = this.codeLines[fileId];
            const feedback = this.feedback.user[fileId];

            const ret = Object.keys(feedback).reduce((res, lineStr) => {
                const line = Number(lineStr);
                const startLine = Math.max(line - this.contextAmount, 0);
                const endLine = Math.min(line + this.contextAmount + 1, lines.length);

                if (res.length === 0 || last(last(res)) <= startLine - 2) {
                    res.push([startLine, endLine]);
                } else {
                    last(res)[1] = endLine;
                }

                return res;
            }, []);

            return ret;
        },
    },

    components: {
        Loader,
        FeedbackArea,
        InnerCodeViewer,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.feedback-overview {
    max-height: 100%;
    overflow: hidden;
    display: flex;
}

.scroller {
    width: 100%;
    flex: 1 1 auto;
    overflow: auto;
}

.inner-code-viewer {
    overflow: hidden;
}

.general-feedback {
    white-space: pre-wrap;

    #app.dark & {
        color: @text-color-dark;
    }
}
</style>

<style lang="less">
.feedback-overview > .scroller > .card {
    border-left-width: 0px;
    border-right-width: 0px;

    &:first-child {
        border-top-width: 0px;
    }

    &:last-child {
        border-bottom-width: 0px;
    }

    &:not(:first-child) {
        &,
        & > .card-header {
            border-top-left-radius: 0;
            border-top-right-radius: 0;
        }
    }

    &:not(:last-child) {
        margin-bottom: -1px;
        border-bottom-left-radius: 0;
        border-bottom-right-radius: 0;
    }

    > .card-header {
        position: sticky;
        top: -1px;
        border-top-width: 1px;
        border-top-style: solid;
        border-top-color: inherit;
        border-radius: 0;
        margin-top: -1px;
        z-index: 100;
        background-color: #f7f7f7;
    }
}
</style>
