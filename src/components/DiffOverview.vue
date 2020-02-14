<template>
<b-alert class="error" variant="danger" show v-if="error">
    <div v-html="error"/>
</b-alert>

<loader v-else-if="loading" />

<div v-else class="diff-overview border rounded">
    <div class="scroller">
        <b-card v-if="newFiles.length + deletedFiles.length === 0"
                header="Added and deleted files">
            <span class="text-muted font-italic">
                No files were added or deleted.
            </span>
        </b-card>

        <template v-else>
            <b-card header="Added files">
                <span v-if="newFiles.length === 0"
                      class="text-muted font-italic">
                    No files were added
                </span>

                <ul v-else>
                    <li v-for="f in newFiles"  :key="`file-added-${f.ids[1]}`">
                        <router-link :to="getFileLink(f.ids[1], 'teacher')">
                            <code>{{ f.fullName }}</code>
                        </router-link>
                    </li>
                </ul>
            </b-card>

            <b-card header="Deleted files">
                <span v-if="deletedFiles.length === 0"
                      class="text-muted font-italic">
                    No files were deleted
                </span>

                <ul v-else>
                    <li v-for="f in deletedFiles"
                        :key="`file-deleted-${f.ids[0]}`">
                        <router-link :to="getFileLink(f.ids[0], 'student')">
                            <code>{{ f.fullName }}</code>
                        </router-link>
                    </li>
                </ul>
            </b-card>
        </template>

        <b-card v-if="changedFiles.length === 0"
                header="Changes">
            <span class="text-muted font-italic">
                No files were changed
            </span>
        </b-card>

        <b-card v-for="f in changedFiles"
                :key="`file-${f.ids[0]}-${f.ids[1]}`">
            <template slot="header">
                <router-link :to="getFileLink(f.ids[0], 'diff')">
                    {{ f.fullName }}
                </router-link>
            </template>

            <diff-viewer class="border rounded p-0"
                         :file="f"
                         :show-whitespace="showWhitespace"
                         diff-only />
        </b-card>
    </div>
</div>
</template>

<script>
import { mapActions } from 'vuex';

import Loader from './Loader';
import DiffViewer from './DiffViewer';

export default {
    name: 'diff-overview',

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
    },

    data() {
        return {
            error: '',
        };
    },

    computed: {
        fileTree() {
            return this.submission.fileTree;
        },

        loading() {
            return !this.fileTree;
        },

        allModifiedFiles() {
            return this.getChangedFiles(this.fileTree.diff);
        },

        changedFiles() {
            return this.allModifiedFiles.changed;
        },

        newFiles() {
            return this.allModifiedFiles.added;
        },

        deletedFiles() {
            return this.allModifiedFiles.deleted;
        },
    },

    watch: {
        submission: {
            immediate: true,
            handler() {
                this.storeLoadFileTree({
                    assignmentId: this.assignment.id,
                    submissionId: this.submission.id,
                });
            },
        },
    },

    methods: {
        ...mapActions('fileTrees', {
            storeLoadFileTree: 'loadFileTree',
        }),

        getChangedFiles(tree, prefix = []) {
            const changed = [];
            const added = [];
            const deleted = [];

            if (!tree || !tree.entries) {
                return { changed, added, deleted };
            }
            tree.entries.forEach(f => {
                if (f.entries) {
                    const res = this.getChangedFiles(f, prefix.concat(f.name));
                    changed.push(...res.changed);
                    added.push(...res.added);
                    deleted.push(...res.deleted);
                } else if (f.ids && f.ids[0] !== f.ids[1] && !((f.ids[0] === f.ids[1]) === null)) {
                    let toChange = changed;
                    if (f.ids[0] == null) {
                        toChange = added;
                    } else if (f.ids[1] == null) {
                        toChange = deleted;
                    }

                    toChange.push(
                        Object.assign({}, f, {
                            fullName: prefix.concat(f.name).join('/'),
                        }),
                    );
                }
            });
            return { changed, added, deleted };
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
    },

    components: {
        Loader,
        DiffViewer,
    },
};
</script>

<style lang="less" scoped>
.diff-overview {
    max-height: 100%;
    overflow: hidden;
    display: flex;
}

.scroller {
    width: 100%;
    flex: 1 1 auto;
    overflow: auto;
}

.diff-viewer {
    overflow: hidden;
}
</style>

<style lang="less">
.diff-overview > .scroller > .card {
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
        & .card-header {
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
