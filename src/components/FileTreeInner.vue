<template>
<div class="file-tree-inner">
    <div class="directory-label"
         :class="{ faded: fadeDirectory }"
         @click.stop="toggle()">
        <span class="label"
              :title="tree.name">
            <icon name="caret-down"
                  class="caret-icon"
                  :class="isCollapsed ? 'collapsed' : 'expanded'"
            /><icon :name="dirIcon"
                    class="dir-icon"
            /><slot name="dir-slot"
                    :depth="depth + 1"
                    :filename="tree.name"
                    :full-filename="`${fullName}/`"
            ><span>{{ tree.name }}</span></slot>
            <sup v-if="depth > 0 && revision && fileTree && fileTree.hasRevision(tree)"
                 v-b-popover.hover.top.window="'This directory contains a file with a teacher\'s revision'"
                 class="rev-popover">
                modified
            </sup>
        </span>
    </div>
    <ol v-show="!isCollapsed"
        v-if="!isCollapsed || depth < 2">
        <li v-for="f in tree.entries"
            class="file"
            :class="{ directory: f.entries, faded: fadeFile(f), active: fileIsSelected(f), 'fade-active': fadeSelected }">
            <file-tree-inner v-if="f.entries"
                             :file-tree="fileTree"
                             :tree="f"
                             :fade-selected="fadeSelected"
                             :revision="revision"
                             :collapsed="shouldCollapseTree(f)"
                             :collapse-function="collapseFunction"
                             :no-links="noLinks"
                             :depth="depth + 1"
                             :parent-dir="fullName"
                             :fade-unchanged="fadeUnchanged">
                <template v-for="slot in Object.keys($scopedSlots)"
                          :slot="slot"
                          slot-scope="scope">
                    <slot :name="slot" v-bind="scope"/>
                </template>
            </file-tree-inner>

            <div v-else class="label">
                <template v-if="noLinks">
                    <icon name="file"
                          class="file-icon"
                    /><slot name="file-slot"
                            :full-filename="`${fullName}/${f.name}`"
                            :filename="f.name"
                            :dir="tree"
                            :depth="depth"
                    >{{ f.name }}</slot>
                </template>
                <router-link v-else
                             :to="getFileRoute(f)"
                             :title="f.name"
                ><icon name="file" class="file-icon"/>{{ f.name }}
                </router-link>
                <sup v-if="revision && fileTree && fileTree.hasRevision(f)"
                     v-b-popover.hover.top.window="revisionPopover(f)"
                     class="rev-popover">
                    <router-link :to="revisedFileRoute(f)"
                                 :title="f.name">
                        diff <code><small>(</small>{{ diffLabels[diffAction(f)] }}<small>)</small></code>
                    </router-link>
                </sup>
            </div>
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

export default {
    name: 'file-tree-inner',

    props: {
        tree: {
            type: Object,
            required: true,
        },
        fileTree: {
            type: Object,
            default: null,
        },
        revision: {
            type: String,
            default: null,
        },
        collapsed: {
            type: Boolean,
            default: false,
        },
        parentDir: {
            type: String,
            default: '',
        },
        depth: {
            type: Number,
            default: 0,
        },
        noLinks: {
            type: Boolean,
            default: false,
        },
        collapseFunction: {
            type: Function,
            required: true,
        },
        fadeUnchanged: {
            type: Boolean,
            default: false,
        },
        icon: {
            type: String,
            default: '',
        },
        fadeSelected: {
            type: Boolean,
            default: false,
        },
    },

    data() {
        return {
            isCollapsed: this.collapsed,
            diffLabels: {
                added: '+',
                changed: '~',
                deleted: '-',
            },
        };
    },

    computed: {
        fullName() {
            return `${this.parentDir}/${this.tree.name}`;
        },

        fadeDirectory() {
            return this.fadeUnchanged && this.depth > 0 && !this.fileTree.hasRevision(this.tree);
        },

        currentFileId() {
            return this.$route.params.fileId;
        },

        currentRevision() {
            return this.$route.query.revision || 'student';
        },

        dirIcon() {
            if (this.icon !== '') {
                return this.icon;
            } else {
                return this.isCollapsed ? 'folder' : 'folder-open';
            }
        },

        fileId() {
            return this.$route.params.fileId;
        },
    },

    watch: {
        currentRevision: {
            immediate: true,
            handler() {
                // Expand this directory if it was collapsed and the current file is in this
                // directory.
                if (
                    this.revision === this.currentRevision &&
                    this.fileTree.findFileInDir(this.tree, this.currentFileId)
                ) {
                    this.isCollapsed = false;
                }
            },
        },
    },

    methods: {
        getFileRoute(file) {
            const params = {
                fileId: file.id || file.ids[0] || file.ids[1],
            };

            const query = {};
            if (this.revision) {
                query.revision = this.revision;
            }

            return this.$utils.deepExtend({}, this.$route, {
                name: 'submission_file',
                params,
                query,
            });
        },

        revisedFileRoute(f) {
            let fileId;

            if (f.ids != null) {
                fileId = f.ids[0] == null ? f.ids[1] : f.ids[0];
            } else {
                fileId = f.id;
            }

            return this.$utils.deepExtend({}, this.$route, {
                params: { fileId },
                query: { revision: 'diff' },
            });
        },

        fileIsSelected(f) {
            if (this.revision !== this.currentRevision) {
                return false;
            }

            let fileIds;

            if (f.ids) {
                fileIds = new Set(f.ids);
            } else {
                fileIds = new Set([f.id]);
            }

            return fileIds.has(this.currentFileId);
        },

        fileInTree(fileId, tree) {
            // This property depends on the return value of this function for
            // the parent. If the parent doesn't have the file in its tree this
            // component will also not have it.
            if (this.collapsed) {
                return false;
            }

            const todo = [...tree.entries];

            for (let i = 0; i < todo.length; i++) {
                const child = todo[i];
                if (child.entries) {
                    todo.push(...child.entries);
                } else if (child.id === fileId) {
                    return true;
                }
            }
            return false;
        },

        toggle() {
            this.isCollapsed = !this.isCollapsed;
        },

        fadeFile(f) {
            return this.fadeUnchanged && !this.fileTree.hasRevision(f);
        },

        shouldCollapseTree(dir) {
            return (
                !this.fileInTree(this.fileId, dir) &&
                this.collapseFunction(`${this.fullName}/${dir.name}/`)
            );
        },

        diffAction(f) {
            if (f.ids !== undefined) {
                if (f.ids[0] == null) {
                    return 'added';
                } else if (f.ids[1] == null) {
                    return 'deleted';
                } else {
                    return 'changed';
                }
            } else if (this.fileTree.hasRevision(f)) {
                if (this.fileTree.getRevisionId(f) == null) {
                    return this.revision === 'student' ? 'deleted' : 'added';
                } else {
                    return 'changed';
                }
            } else {
                throw ReferenceError(`File '${f.name} doesn't have a revision.`);
            }
        },

        revisionPopover(f) {
            const action = this.diffAction(f);
            return `This file was ${action} in the teacher's revision. Click here to see the diff`;
        },
    },

    components: {
        Icon,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.file-tree-inner {
    user-select: none;
    cursor: default;
    color: @color-primary;

    #app.dark & {
        color: @text-color-dark;
    }

    a {
        &:hover {
            cursor: pointer;
            text-decoration: underline;
        }

        #app.dark & {
            &,
            &:hover {
                color: @text-color-dark;
            }
        }
    }

    .label {
        text-overflow: ellipsis;
        white-space: nowrap;
        overflow-x: hidden;
        display: block;
        max-width: 100%;
    }

    .directory-label .label:hover {
        cursor: pointer;
    }

    ol {
        list-style: none;
        margin: 0;
        padding: 0;
        overflow: hidden;
    }

    ol,
    .file:not(.directory) {
        padding-left: 1.2rem;
    }

    .file,
    .directory-label {
        &.faded > .label {
            opacity: 0.6;
        }

        &.active > .label {
            opacity: 1;
            font-weight: bold;
        }

        &.active.fade-active > .label {
            opacity: 0.6;
        }
    }

    .caret-icon {
        width: 1em;
        transform: translateY(3px) rotate(0);
        transition: transform @transition-duration;

        &.collapsed {
            transform: translateY(3px) rotate(-90deg);
        }
    }

    .dir-icon {
        width: 1.5em;
        margin-right: 0.2rem;
        transform: translateY(2px);
    }

    .file-icon {
        width: 1em;
        margin-right: 0.5em;
        transform: translateY(2px);
    }

    .rev-popover {
        display: inline;
        font-weight: normal;
    }
}
</style>
