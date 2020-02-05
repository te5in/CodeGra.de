<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<loader v-if="!fileTree"
        class="text-center"
        :scale="3" />
<div v-else
     class="file-tree p-2">
    <file-tree-inner :file-tree="fileTree"
                     :tree="fileTree.student"
                     :collapse-function="collapseFunction"
                     collapsed
                     revision="student"
                     :icon="submission.user.group ? 'user-plus' : 'user'"
                     class="student-tree">
        <span slot="dir-slot" :title="$utils.nameOfUser(submission.user)">
            <description-popover placement="top" boundary="window">
                This directory contains the files uploaded by the student.
            </description-popover>{{
                $utils.nameOfUser(submission.user)
            }}
            <!-- The <user> component does not work here, for some reason it is never visible -->
            <!-- when the user is a group. If this is a group submission it is used in the -->
            <!-- submission navbar, though, so it is not really needed here. -->
        </span>
    </file-tree-inner>

    <template v-if="showRevisions">
        <hr class="my-2" style="margin: 0 -.5rem">

        <file-tree-inner :file-tree="fileTree"
                         :tree="fileTree.teacher"
                         :collapse-function="collapseFunction"
                         collapsed
                         fade-unchanged
                         revision="teacher"
                         icon="graduation-cap"
                         class="teacher-tree">
            <template slot="dir-slot">
                <description-popover placement="top" boundary="window">
                    This directory contains files changed by the teacher. Faded files are unchanged.
                </description-popover
                >Teacher revision
            </template>
        </file-tree-inner>

        <hr class="my-2" style="margin: 0 -.5rem">

        <file-tree-inner :file-tree="fileTree"
                         :tree="fileTree.diff"
                         :collapse-function="collapseFunction"
                         collapsed
                         fade-unchanged
                         revision="diff"
                         icon="diff"
                         class="diff-tree">
            <template slot="dir-slot">
                <description-popover placement="top" boundary="window">
                    This directory contains the diffs between the student submission and the teacher
                    revision. Faded files are unchanged.
                </description-popover
                >Teacher diff
            </template>
        </file-tree-inner>
    </template>

    <template v-if="fileTree.autotest">
        <hr class="my-2" style="margin: 0 -.5rem">

        <file-tree-inner :file-tree="fileTree"
                         :tree="fileTree.autotest"
                         :collapse-function="collapseFunction"
                         collapsed
                         revision="autotest"
                         icon="rocket"
                         class="autotest-tree">
            <template slot="dir-slot">
                <description-popover placement="top" boundary="window">
                    This directory contains files generated during the AutoTest. Each subdirectory
                    represents a single AutoTest category and contains only the files that were
                    generated in that category.
                </description-popover
                >AutoTest output
            </template>
        </file-tree-inner>
    </template>
</div>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';

import 'vue-awesome/icons/user-plus';
import 'vue-awesome/icons/user';
import 'vue-awesome/icons/graduation-cap';
import 'vue-awesome/icons/rocket';

import DescriptionPopover from './DescriptionPopover';
import FileTreeInner from './FileTreeInner';
import Loader from './Loader';
import User from './User';

export default {
    name: 'file-tree',

    props: {
        assignment: {
            type: Object,
            required: true,
        },
        submission: {
            type: Object,
            required: true,
        },
        collapsed: {
            type: Boolean,
            default: true,
        },
        collapseFunction: {
            type: Function,
            default: () => true,
        },
        canSeeRevision: {
            type: Boolean,
            default: false,
        },
        revision: {
            type: String,
            default: '',
        },
    },

    computed: {
        ...mapGetters('fileTrees', ['getFileTree']),

        fileTree() {
            return this.getFileTree(this.assignment.id, this.submission.id);
        },

        showRevisions() {
            return this.canSeeRevision && this.fileTree.hasRevision(this.fileTree.student);
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
    },

    components: {
        DescriptionPopover,
        FileTreeInner,
        Loader,
        User,
    },
};
</script>