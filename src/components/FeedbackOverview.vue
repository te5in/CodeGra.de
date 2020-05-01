<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<b-alert class="error" variant="danger" show v-if="error">
    <div v-html="error"/>
</b-alert>

<loader page-loader v-else-if="loading" />

<div v-else-if="!canSeeFeedback" class="feedback-overview p-3 border rounded font-italic text-muted">
    The feedback is not yet available.
</div>

<div v-else-if="hideEmptyGeneral && !generalFeedback && !hasUserFeedback"
     class="feedback-overview p-3 border rounded font-italic text-muted"
     style="background: white">
    No feedback given.
</div>

<div v-else class="feedback-overview border rounded">
    <div class="scroller">
        <b-card header="General feedback"
                class="general-feedback"
                v-if="!hideEmptyGeneral || generalFeedback">
            <pre v-if="generalFeedback"
                 class="text-wrap-pre mb-0">{{ generalFeedback }}</pre>
            <span v-else class="text-muted font-italic">
                No general feedback given.
            </span>
        </b-card>

        <b-card v-if="fileIds.length === 0"
                header="Inline feedback"
                class="inline-feedback"
                body-class="text-muted font-italic">
            <template v-if="filter">
                No comments match the filter.
            </template>

            <template v-else>
                This submission has no inline feedback.
            </template>
        </b-card>

        <template v-else>
            <b-card v-for="id in fileIds"
                    :key="id"
                    class="inline-feedback">
                <router-link slot="header" :to="getFileLink(id)">
                    {{ fileTree.flattened[id] }}
                </router-link>

                <div v-if="disabledFileType(id)">
                    Overview mode is not available for {{ disabledFileType(id).name }}. Click
                    <router-link class="inline-link" :to="getFileLink(id)">here</router-link>
                    to see the entire file.

                    <feedback-area v-if="disabledFileType(id).singleLine && showInlineFeedback"
                                   class="pt-2"
                                   :can-use-snippets="false"
                                   :line="0"
                                   :feedback="feedback.user[id][0]"
                                   :total-amount-lines="0"
                                   :assignment="assignment"
                                   :submission="submission"
                                   :non-editable="nonEditable"
                                   :should-fade-reply="shouldFadeReply"/>
                </div>

                <div v-else-if="codeLines[id] == null">
                    <loader/>
                </div>
                <div v-else
                     v-for="(part, i) in getParts(id)"
                     :key="`file-${id}-line-${part[0]}`">
                    <hr v-if="i !== 0">

                    <inner-code-viewer class="border rounded p-0"
                                       :assignment="assignment"
                                       :submission="submission"
                                       :code-lines="codeLines[id]"
                                       :feedback="showInlineFeedback ? (feedback.user[id] || {}) : {}"
                                       :linter-feedback="feedback.linter[id]"
                                       :file-id="id"
                                       :start-line="part[0]"
                                       :end-line="part[1]"
                                       :show-whitespace="showWhitespace"
                                       :non-editable="nonEditable"
                                       :should-render-thread="shouldRenderThread"
                                       :should-fade-reply="shouldFadeReply"/>
                </div>
            </b-card>
        </template>
    </div>
</div>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';

import { Assignment, Submission } from '@/models';
import { mapObject } from '@/utils';
import decodeBuffer from '@/utils/decode';

import Loader from './Loader';
import InnerCodeViewer from './InnerCodeViewer';
import FeedbackArea from './FeedbackArea';

export default {
    name: 'feedback-overview',

    props: {
        assignment: {
            type: Assignment,
            required: true,
        },
        submission: {
            type: Submission,
            required: true,
        },
        showWhitespace: {
            type: Boolean,
            default: true,
        },
        showInlineFeedback: {
            type: Boolean,
            default: true,
        },
        nonEditable: {
            type: Boolean,
            default: false,
        },
        filter: {
            type: String,
            default: null,
        },
        hideEmptyGeneral: {
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
            return this.submission && this.submission.fileTree;
        },

        feedback() {
            return this.submission && this.submission.feedback;
        },

        filteredUserFeedback() {
            if (this.feedback == null) {
                return null;
            }

            if (this.filter == null || this.filter === '') {
                return mapObject(this.feedback.user, fileFb =>
                    mapObject(fileFb, thread => new Set(thread.replies.map(reply => reply.id))),
                );
            }

            const regex = new RegExp(this.filter, 'i');

            return Object.entries(this.feedback.user).reduce((fb, [fileId, fileFb]) => {
                const filteredFileFb = Object.values(fileFb).reduce((acc, thread) => {
                    const matchingReplies = thread.replies.filter(reply =>
                        regex.test(reply.message),
                    );
                    if (matchingReplies.length > 0) {
                        acc[thread.line] = new Set(matchingReplies.map(reply => reply.id));
                    }
                    return acc;
                }, {});
                if (Object.keys(filteredFileFb).length > 0) {
                    fb[fileId] = filteredFileFb;
                }
                return fb;
            }, {});
        },

        fileIds() {
            // Because the submission's fileTree and feedback are loaded simultaneously, it is
            // possible that the fileTree is not set when the feedback changes. The rest of the
            // component, however, depends on the fact that both are non-null, and because almost
            // everything works via computed properties, we wait with returning the file ids that
            // need to be rendered until the fileTree has been loaded.
            if (this.fileTree == null || this.feedback == null) {
                return [];
            }
            return Object.keys(this.filteredUserFeedback);
        },

        nonDisabledFileIds() {
            return this.fileIds.filter(id => !this.disabledFileType(id));
        },

        generalFeedback() {
            return this.feedback.general;
        },

        submissionId() {
            return this.submission.id;
        },

        canSeeFeedback() {
            return this.assignment.canSeeUserFeedback();
        },

        hasUserFeedback() {
            return Object.keys(this.feedback.user).length > 0;
        },
    },

    watch: {
        submissionId: {
            immediate: true,
            handler() {
                this.loadFeedback();
            },
        },

        nonDisabledFileIds: {
            immediate: true,
            handler() {
                this.loadCode();
            },
        },
    },

    methods: {
        ...mapActions('feedback', {
            storeLoadSubmissionFeedback: 'loadFeedback',
        }),
        ...mapActions('fileTrees', {
            storeLoadSubmissionFileTree: 'loadFileTree',
        }),
        ...mapActions('code', { storeLoadCode: 'loadCode' }),

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
            if (this.fileIds.length === 0) {
                this.codeLines = {};
                return;
            }

            if (this.codeLines == null) {
                this.codeLines = {};
            }

            this.nonDisabledFileIds.filter(id => this.codeLines[id] == null).map(async id => {
                this.$set(this.codeLines, id, await this.loadCodeWithSettings(id));
            });
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
            return this.storeLoadCode(fileId).then(
                rawCode => {
                    let code;
                    try {
                        code = decodeBuffer(rawCode);
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

        getFileLink(fileId) {
            const revision = this.fileTree.getRevision(fileId);
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
            const feedback = this.filteredUserFeedback[fileId];

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

        shouldRenderThread(thread) {
            return this.$utils.getProps(
                this.filteredUserFeedback,
                null,
                thread.fileId,
                thread.line,
            ) != null;
        },

        shouldFadeReply(thread, reply) {
            return this.shouldRenderThread(thread) &&
                !this.filteredUserFeedback[thread.fileId][thread.line].has(reply.id);
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

.general-feedback pre {
    @{dark-mode} {
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
        background-color: rgb(247, 247, 247);
    }
}
</style>
