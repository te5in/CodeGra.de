<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<loader v-if="!fileTree"
        class="text-center"
        :scale="3" />
<div v-else
     class="file-tree px-2 pb-2"
     :class="{ 'pt-2': !showRevisions, 'pt-0': showRevisions }">
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
                   v-b-popover.hover.bottom="'No revision'"
                   :title="option.title"/>
        </b-tabs>

        <description-popover placement="top" boundary="window">
            Choose to view either the student's submitted files, the revised files as edited by a
            teacher or teaching assistant, or a diff between the two versions.

            <p v-if="!fileTree.hasRevision(currentTree)" style="margin: 1rem 0 0;">
                This submission has no revisions.
            </p>
        </description-popover>
    </div>

    <file-tree-inner :file-tree="fileTree"
                     :tree="currentTree"
                     :revision="revision"
                     :collapse-function="collapseFunction" />
</div>
</template>

<script>
import { mapActions } from 'vuex';

import DescriptionPopover from './DescriptionPopover';
import FileTreeInner from './FileTreeInner';
import Loader from './Loader';

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
            default: 'student',
        },
    },

    data() {
        return {
            revisionOptions: [
                {
                    title: 'Student',
                    value: 'student',
                },
                {
                    title: 'Teacher',
                    value: 'teacher',
                },
                {
                    title: 'Diff',
                    value: 'diff',
                },
            ],
        };
    },

    computed: {
        fileId() {
            return Number(this.$route.params.fileId) || null;
        },

        fileTree() {
            return this.submission && this.submission.fileTree;
        },

        currentTree() {
            return this.fileTree && this.fileTree[this.revision];
        },

        selectedRevision() {
            let revision = this.revisionOptions.findIndex(opt => opt.value === this.revision);

            if (revision < 0 || this.revisionOptions[revision].disabled) {
                revision = 0;
            }

            return revision;
        },

        showRevisions() {
            return (
                this.canSeeRevision &&
                (this.revision !== 'student' || this.fileTree.hasRevision(this.fileTree.student))
            );
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
        ...mapActions('courses', {
            storeLoadFileTree: 'loadSubmissionFileTree',
        }),

        revisionChanged(index) {
            this.$emit('revision', this.revisionOptions[index].value);
        },
    },

    components: {
        DescriptionPopover,
        FileTreeInner,
        Loader,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.revision-container {
    position: relative;
    position: sticky;
    top: 0;
    margin: 0 -0.5rem 0.875rem;
    padding: 0.5rem 0.75rem 0;
    border-bottom: 1px solid rgba(0, 0, 0, 0.15);
    background-color: @footer-color;

    #app.dark & {
        background-color: @color-primary-darker;
    }

    .tabs {
        flex: 1 1 auto;
        overflow: auto;
        margin: 0 -0.75rem -1px -0.75rem;
        padding: 0 0.75rem 0 0.75rem;

        .revision-tabs-wrapper {
            width: auto;
        }
    }

    .description-popover {
        position: absolute;
        top: 0;
        bottom: 0.75rem;
        right: 0;
        width: 1.5rem;
        padding-top: 0.95rem;
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
