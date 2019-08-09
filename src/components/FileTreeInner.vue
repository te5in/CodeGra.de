<template>
<div class="file-tree-inner">
    <div class="directory"
         :class="{ faded: fadeDirectory }"
         @click.stop="toggle()">
        <span class="label"
              :title="tree.name">
            <icon name="caret-down"
                  class="caret-icon"
                  :class="isCollapsed ? 'collapsed' : 'expanded'"
            /><icon name="folder"
                    class="dir-icon"
                    v-if="isCollapsed"
            /><icon name="folder-open"
                    class="dir-icon"
                    v-else
            /><slot name="dir-slot"
                    :depth="depth + 1"
                    :filename="tree.name"
                    :full-filename="`${fullName}/`"
            ><span>{{ tree.name }}</span></slot>
            <sup v-if="depth > 0 && revision && fileTree.hasRevision(tree)"
                 v-b-popover.hover.top.window="'This directory has a file with a teacher\'s revision'"
                 class="rev-popover">
                modified
            </sup>
        </span>
    </div>
    <ol v-show="!isCollapsed"
        v-if="!isCollapsed || depth < 2">
        <li v-for="f in tree.entries"
            class="file"
            :class="{ faded: fadeFile(f), active: fileIsSelected(f) }">
            <file-tree-inner v-if="f.entries"
                             :file-tree="fileTree"
                             :tree="f"
                             :revision="revision"
                             :collapsed="shouldCollapseTree(f)"
                             :collapse-function="collapseFunction"
                             :no-links="noLinks"
                             :depth="depth + 1"
                             :parent-dir="fullName">
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
                             :title="f.name">
                    <icon name="file" class="file-icon"/>{{ f.name }}
                </router-link>
                <sup v-if="revision && fileTree.fileHasRevision(f)"
                    v-b-popover.hover.top.window="revisionPopover(f)"
                    class="rev-popover">
                    <router-link :to="revisedFileRoute(f)"
                                 :title="f.name"
                                 @click="$emit('revision', 'diff')">
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
            return this.depth > 0 && this.diffMode && !this.fileTree.hasRevision(this.tree);
        },

        diffMode() {
            return this.revision === 'diff';
        },
    },

    methods: {
        getFileRoute(file) {
            const fileId = file.id || file.ids[0] || file.ids[1];

            return this.$utils.deepExtend({}, this.$route, {
                name: 'submission_file',
                params: { fileId },
            });
        },

        revisedFileRoute(f) {
            let fileId;

            if (f.ids != null) {
                fileId = f.ids[1] == null ? f.ids[0] : f.ids[1];
            } else if (f.revision != null) {
                fileId = f.revision.id;
            } else if (f.revision === null) {
                fileId = f.id;
            } else {
                throw ReferenceError(`File '${f.name}' doesn't have a revision.`);
            }

            return this.$utils.deepExtend({}, this.$route, {
                params: { fileId },
                query: { revision: 'diff' },
            });
        },

        fileIsSelected(f) {
            const selectedId = this.$route.params.fileId;
            const fileId = f.id || (f.ids && (f.ids[0] || f.ids[1]));
            return Number(selectedId) === Number(fileId);
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
                } else if (Number(child.id) === Number(fileId)) {
                    return true;
                }
            }
            return false;
        },

        toggle() {
            this.isCollapsed = !this.isCollapsed;
        },

        fadeFile(f) {
            return this.diffMode && !this.fileTree.fileHasRevision(f);
        },

        shouldCollapseTree(dir) {
            return (
                !this.fileInTree(this.$route.params.fileId, dir) &&
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
            } else if (f.revision !== undefined) {
                if (f.revision == null) {
                    return 'deleted';
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

    .directory .label:hover {
        cursor: pointer;
    }

    ol {
        list-style: none;
        margin: 0;
        padding: 0;
        padding-left: 1.2rem;
        overflow: hidden;
    }

    .file,
    .directory {
        &.faded > .label {
            opacity: 0.6;
        }

        &.active > .label {
            opacity: 1;
            font-weight: bold;
        }
    }

    .caret-icon {
        width: 1em;
        transform: rotate(0);
        transition: transform @transition-duration;

        &.collapsed {
            transform: rotate(-90deg);
        }
    }

    .dir-icon {
        width: 1.5em;
    }

    .file-icon {
        width: 1em;
        margin-right: 0.5em;
    }

    .rev-popover {
        display: inline;
        font-weight: normal;
    }
}
</style>
