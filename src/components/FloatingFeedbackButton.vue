<template>
<div class="floating-feedback-button"
     :class="{ 'add-space': addSpace, 'without-hover': visibleWithoutHover }">
    <div class="content">
        <div class="content-wrapper">
            <slot/>
        </div>

        <b-button class="feedback-button"
                  :class="buttonClasses"
                  @click="startEditingFeedback"
                  v-b-popover.window.top.hover="`Edit feedback for this ${slotDescription}`"
                  v-if="editable && !disabled">
            <icon name="edit"/>
        </b-button>
    </div>
    <feedback-area
        :class="{ 'feedback-editable': editable }"
        ref="feedbackArea"
        :editing="editingFeedback"
        :editable="editable"
        :feedback="feedback.msg"
        :author="feedback && feedback.author"
        :line="line"
        :file-id="fileId"
        :total-amount-lines="line + 1000"
        :forceSnippetsAbove="snippetFieldAbove"
        :can-use-snippets="canUseSnippets"
        :assignment="assignment"
        :submission="submission"
        @editFeedback="editingFeedback = true"
        @feedbackChange="feedbackChange"
        v-if="hasFeedback && !disabled"/>
</div>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';

import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/edit';

import FeedbackArea from './FeedbackArea';

export default {
    name: 'floating-feedback-button',

    data() {
        return {
            editingFeedback: false,
        };
    },

    props: {
        fileId: {
            type: String,
            required: true,
        },
        line: {
            type: Number,
            required: true,
        },
        feedback: {
            type: Object,
            default: () => ({}),
        },
        editable: {
            type: Boolean,
            default: false,
        },
        canUseSnippets: {
            type: Boolean,
            default: false,
        },
        slotDescription: {
            type: String,
            default: 'cell',
        },
        alwaysShowButton: {
            type: Boolean,
            default: false,
        },
        disabled: {
            type: Boolean,
            default: false,
        },
        snippetFieldAbove: {
            type: Boolean,
            default: false,
        },
        assignment: {
            type: Object,
            required: true,
        },
        submission: {
            type: Object,
            required: true,
        },
        addSpace: {
            type: Boolean,
            default: false,
        },
        visibleWithoutHover: {
            type: Boolean,
            default: false,
        },
        buttonPosition: {
            type: String,
            default: 'top-right',
        },
    },

    computed: {
        ...mapGetters('user', {
            myId: 'id',
        }),

        hasFeedback() {
            return this.feedback && this.feedback.msg != null;
        },

        buttonClasses() {
            const res = { hide: this.hasFeedback && !this.alwaysShowButton };
            this.buttonPosition.split('-').forEach(pos => {
                res[pos] = true;
            });
            return res;
        },
    },

    methods: {
        ...mapActions('feedback', {
            storeAddFeedbackLine: 'addFeedbackLine',
        }),

        feedbackChange() {
            this.editingFeedback = false;
        },

        async startEditingFeedback() {
            this.editingFeedback = true;
            if (!this.hasFeedback) {
                await this.storeAddFeedbackLine({
                    assignmentId: this.assignment.id,
                    submissionId: this.submission.id,
                    fileId: this.fileId,
                    line: this.line,
                    author: { id: this.myId },
                });
            }
            this.$nextTick(() => {
                const ref = this.$refs.feedbackArea;
                if (ref) {
                    const el = ref.$el.querySelector('textarea');
                    if (el) {
                        el.focus();
                    }
                }
            });
        },
    },

    components: {
        Icon,
        FeedbackArea,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.floating-feedback-button {
    display: flex;
    flex-direction: column;
    max-height: 100%;
    overflow: hidden;

    @media @media-no-large {
        height: 100%;
    }
}

.content {
    position: relative;
    flex: 1 1 auto;
    min-height: 0;
    display: flex;
    flex-direction: column;
}

.content-wrapper {
    width: 100%;
    height: 100%;
    overflow: auto;
    display: block;
}

.feedback-area-wrapper {
    flex: 0 0 auto;
}

.feedback-area {
    padding-top: 0 !important;
}

.feedback-button.btn {
    position: absolute;

    &.top {
        top: 0;
    }
    &.bottom {
        bottom: 0;
    }
    &.right {
        right: 0;
    }
    &.left {
        left: 0;
    }

    .add-space & {
        margin: 1rem;
    }

    transition-property: opacity, transform;
    transition-duration: @transition-duration;
    transform: scale(0);
    opacity: 0;

    .floating-feedback-button:hover &:not(.hide),
    .floating-feedback-button.without-hover &:not(.hide) {
        transform: scale(1);
        opacity: 1;
    }
}

.feedback-editable {
    cursor: pointer;
}
</style>

<style lang="less">
.floating-feedback-button .feedback-area.edit.feedback-editable {
    padding-bottom: 0;
}

.floating-feedback-button.add-space {
    .feedback-area-wrapper {
        margin: 0 -1px -1px;
        border-top-left-radius: 0 !important;
        border-top-right-radius: 0 !important;
    }

    .feedback-area {
        margin: 0 -1px -1px;

        textarea {
            border-top-left-radius: 0 !important;
        }

        .submit-feedback .submit-button {
            border-top-right-radius: 0 !important;
        }
    }
}
</style>
