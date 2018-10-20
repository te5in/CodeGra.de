<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="file-tree"
     :class="{ collapsed: isCollapsed, 'no-top-padding': showRevisions }">
    <div v-if="showRevisions"
         class="revision-container">

        <b-tabs small
                :value="selectedRevision"
                @input="revisionChanged"
                nav-class="revision-tabs"
                nav-wrapper-class="revision-tabs-wrapper">
            <b-tab v-for="option in revisionOptions"
                   :key="option.value"
                   :disabled="option.disabled"
                   v-b-popover.hover.bottom="'No rev'"
                   :title="option.title"/>
        </b-tabs>

        <description-popover placement="bottom">
            <span slot="description">
                Choose to view either the student's submitted files, the revised files as edited by a
                teacher or teaching assistant, or a diff between the two versions.

                <p v-if="!dirHasRevision(tree)" style="margin: 1rem 0 0;">
                    This submission has no revisions.
                </p>
            </span>
        </description-popover>
    </div>

    <div class="directory" :class="{ faded: depth > 0 && diffMode && !dirHasRevision(tree) }" @click.stop="toggle()">
        <span class="label">
            <icon name="caret-right" class="caret-icon" v-if="isCollapsed"/>
            <icon name="caret-down" class="caret-icon" v-else/>
            <icon name="folder" class="dir-icon" v-if="isCollapsed"/>
            <icon name="folder-open" class="dir-icon" v-else/>
            {{ tree.name }}
            <sup v-if="depth > 0 && dirHasRevision(tree)"
                    v-b-popover.hover.top="'This directory has a file with a teacher\'s revision'"
                    class="rev-popover">
                modified
            </sup>
        </span>
    </div>
    <ol v-show="!isCollapsed">
        <li v-for="f in tree.entries"
            class="file"
            :class="{ faded: diffMode && !fileHasRevision(f), active: fileIsSelected(f) }">
            <file-tree :tree="f"
                       :collapsed="!fileInTree($route.params.fileId, f)"
                       :depth="depth + 1"
                        v-if="f.entries"/>
            <router-link :to="getFileRoute(f)"
                         class="label"
                         v-else>
                <icon name="file" class="file-icon"/>{{ f.name }}
            </router-link>
            <sup v-if="fileHasRevision(f)"
                 v-b-popover.hover.top="revisionPopover(f)"
                 class="rev-popover">
                <router-link v-if="!diffMode"
                             :to="revisedFileRoute(f)"
                             @click="$emit('revision', 'diff')">
                    diff
                </router-link>
                <span v-else>diff</span>
            </sup>
        </li>
    </ol>
</div>
</template>

<script>
import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/folder';
import 'vue-awesome/icons/folder-open';
import 'vue-awesome/icons/file';
import 'vue-awesome/icons/caret-right';
import 'vue-awesome/icons/caret-down';

import { DescriptionPopover } from '@/components';

export default {
    name: 'file-tree',

    props: {
        tree: {
            type: Object,
            default: null,
        },
        collapsed: {
            type: Boolean,
            default: true,
        },
        depth: {
            type: Number,
            default: 0,
        },
        canSeeRevision: {
            type: Boolean,
            default: false,
        },
        revision: {
            type: String,
            default: 'student',
        },
    },

    data() {
        return {
            isCollapsed: this.collapsed,
            revisionOptions: [
                {
                    title: 'Student',
                    value: 'student',
                }, {
                    title: 'Teacher',
                    value: 'teacher',
                }, {
                    title: 'Diff',
                    value: 'diff',
                },
            ],
        };
    },

    computed: {
        courseId() {
            return this.$route.params.courseId;
        },

        assignmentId() {
            return this.$route.params.assignmentId;
        },

        submissionId() {
            return this.$route.params.submissionId;
        },

        diffMode() {
            return this.$route.query.revision === 'diff';
        },

        selectedRevision() {
            let revision = this.revisionOptions.findIndex(
                opt => opt.value === this.revision,
            );

            if (revision < 0 || this.revisionOptions[revision].disabled) {
                revision = 0;
            }

            return revision;
        },

        showRevisions() {
            return this.depth === 0 && this.canSeeRevision &&
                (!this.tree.isStudent || this.hasRevision(this.tree));
        },
    },

    methods: {
        toggle() {
            this.isCollapsed = !this.isCollapsed;
        },

        getFileRoute(file) {
            const fileId = file.id || file.ids[0] || file.ids[1];
            return {
                name: 'submission_file',
                params: {
                    courseId: this.courseId,
                    assignmentId: this.assignmentId,
                    submissionId: this.submissionId,
                    fileId,
                },
                query: this.$route.query,
            };
        },

        fileInTree(fileId, tree) {
            for (let i = 0; i < tree.entries.length; i += 1) {
                if (tree.entries[i].entries) {
                    if (this.fileInTree(fileId, tree.entries[i])) {
                        return true;
                    }
                } else if (Number(tree.entries[i].id) === Number(fileId)) {
                    return true;
                }
            }
            return false;
        },

        fileIsSelected(f) {
            const selectedId = this.$route.params.fileId;
            const fileId = f.id || (f.ids && (f.ids[0] || f.ids[1]));
            return Number(selectedId) === Number(fileId);
        },

        hasRevision(f) {
            if (f.entries) {
                return this.dirHasRevision(f);
            }
            return this.fileHasRevision(f);
        },

        fileHasRevision(f) {
            if (f.entries) return false;

            return f.revision !== undefined ||
                (f.ids && f.ids[0] !== f.ids[1]);
        },

        dirHasRevision(d) {
            if (d.revision !== undefined) {
                return true;
            }
            for (let i = 0; i < d.entries.length; i += 1) {
                if (this.hasRevision(d.entries[i])) {
                    return true;
                }
            }
            return false;
        },

        revisionChanged(index) {
            this.$emit('revision', this.revisionOptions[index].value);
        },

        revisedFileRoute(f) {
            let fileId;

            if (f.ids != null) {
                [, fileId] = f.ids;
            } else if (f.revision != null) {
                fileId = f.revision.id;
            } else if (f.revision === null) {
                fileId = f.id;
            } else {
                throw ReferenceError(`File '${f.name}' doesn't have a revision.`);
            }

            return {
                params: { fileId },
                query: Object.assign({}, this.$route.query, {
                    revision: 'diff',
                }),
            };
        },

        revisionPopover(f) {
            let action;

            if (f.ids !== undefined) {
                if (f.ids[0] == null) {
                    action = 'added';
                } else if (f.ids[1] == null) {
                    action = 'deleted';
                } else {
                    action = 'changed';
                }
            } else if (f.revision !== undefined) {
                action = f.revision == null ? 'deleted' : 'changed';
            }

            const text = `This file was ${action} in the teacher's revision.`;

            if (!this.diffMode) {
                return `${text} Click here to see the diff.`;
            } else {
                return text;
            }
        },
    },

    components: {
        DescriptionPopover,
        Icon,
    },
};
</script>

<style lang="less" scoped>
@import "~mixins.less";

.file-tree a,
.file-tree {
    user-select: none;
    cursor: default;
    color: @color-primary;

    #app.dark & {
        color: @text-color-dark;
    }

    &.no-top-padding {
        padding-top: 0;
    }

    a:hover {
        cursor: pointer;
        text-decoration: underline;
    }

    .directory .label:hover {
        cursor: pointer;
    }

    ol {
        list-style: none;
        margin: 0;
        padding: 0;
        padding-left: 1.5em;
        overflow: hidden;
    }

    .file, .directory {
        &.faded > .label {
            opacity: .6;
        }

        &.active > .label {
            opacity: 1;
            font-weight: bold;
        }
    }

    .caret-icon {
        width: 1em;
    }

    .dir-icon {
        width: 1.5em;
    }

    .file-icon {
        width: 1em;
        margin-right: .5em;
    }

    .rev-popover {
        display: inline;
    }
}

.revision-container {
    position: sticky;
    top: 0;
    margin: -.5rem -.75rem .875rem;
    padding: .5rem .75rem 0;
    border-bottom: 1px solid rgba(0, 0, 0, .15);
    background-color: @footer-color;

    #app.dark & {
        background-color: @color-primary-darker;
    }

    .tabs {
        flex: 1 1 auto;
        overflow: auto;
        margin: 0  -.75rem -1px -.75rem;
        padding: 0 .75rem 0 .75rem;

        .revision-tabs-wrapper {
            width: auto;
        }
    }

    .description-popover {
        position: absolute;
        top: 0;
        bottom: .75rem;
        right: 0;
        width: 1.5rem;
        padding-top: .95rem;
        background-color: inherit;
    }
}
</style>

<style lang="less">
.file-tree .revision-container {
    .revision-tabs-wrapper {
        width: max-content;
        padding-right: 1.75rem;
    }

    .revision-tabs {
        width: max-content;
        flex-wrap: nowrap;
    }

    .revision-tabs,
    .nav-link:hover,
    .nav-link.active {
        &,
        #app.dark & {
            border-bottom-color: transparent !important;
        }
    }

    .nav-link.disabled {
        cursor: not-allowed;
    }
}
</style>
