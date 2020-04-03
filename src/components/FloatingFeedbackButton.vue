<template>
<div class="floating-feedback-button"
     :class="{ 'add-space': addSpace, 'without-hover': visibleWithoutHover }">
    <div class="content">
        <div class="content-wrapper">
            <slot/>
        </div>

        <submit-button class="feedback-button"
                       :class="buttonClasses"
                       :submit="addFeedback"
                       @success="afterAddFeedback"
                       variant="secondary"
                       v-b-popover.window.top.hover="`Edit feedback for this ${slotDescription}`"
                       v-if="editable && !disabled && !hasFeedback">
            <icon name="edit"/>
        </submit-button>
    </div>
    <feedback-area
        class="border-top"
        ref="feedbackArea"
        :editable="editable"
        :feedback="feedback"
        :total-amount-lines="1"
        :forceSnippetsAbove="snippetFieldAbove"
        :can-use-snippets="canUseSnippets"
        :submission="submission"
        v-if="hasFeedback && !disabled"/>
</div>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';
import { FeedbackLine } from '@/models';

import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/edit';

import FeedbackArea from './FeedbackArea';
import SubmitButton from './SubmitButton';

export default {
    name: 'floating-feedback-button',

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
            type: FeedbackLine,
            default: null,
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
            return this.feedback != null && !this.feedback.isEmpty;
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

        addFeedback() {
            return FeedbackLine.createFeedbackLine(
                parseInt(this.fileId, 10),
                this.line,
                this.myId,
            );
        },

        afterAddFeedback({ cgResult }) {
            this.storeAddFeedbackLine({
                assignmentId: this.assignment.id,
                submissionId: this.submission.id,
                line: cgResult,
            });
        },
    },

    components: {
        Icon,
        FeedbackArea,
        SubmitButton,
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
    display: flex;
    flex-direction: column;
    overflow-y: auto;
    min-height: 0;
}

.content-wrapper {
    width: 100%;
    height: 100%;
    overflow: auto;
    max-height: 100%;
    display: flex;
    flex-direction: column;
    flex: 1 1 auto;
}

.feedback-area {
    flex: 1 0 auto;
    max-height: 80%;
    overflow-y: auto;
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
</style>

<style lang="less">
.floating-feedback-button .feedback-area {
    padding: 0.5rem;
}

.floating-feedback-button.add-space {
    .feedback-area {
        textarea {
            border-top-left-radius: 0 !important;
        }

        .submit-feedback .submit-button {
            border-top-right-radius: 0 !important;
        }
    }
}
</style>
