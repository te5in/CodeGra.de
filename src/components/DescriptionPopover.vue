<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<span class="description-popover"
      :class="{ 'float-right': !hugText }"
      @click.stop.prevent>
    <b-popover :placement="placement"
               :triggers="triggers"
               :show="show"
               :target="compId"
               :boundary="boundary"
               :title="title">
        <div class="description-popover-content">
            <slot name="description">{{ description }}</slot>
            <slot v-if="!!$slots.default"/>
        </div>
    </b-popover>
    <component :is="hugText ? 'sup' : 'span'"
               class="desc-pop-span"
               :id="compId">
        <span :title="spanTitle">
            <icon :name="icon" scale="0.75"/>
        </span>
    </component>
</span>
</template>

<script>
import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/info';

let i = 0;

export default {
    name: 'description-popover',

    data() {
        return {
            compId: `description-popover-i-${i++}`,
        };
    },

    props: {
        description: {
            type: String,
        },

        spanTitle: {
            default: 'Click to show help',
        },

        triggers: {
            type: [String, Array],
            default: 'click',
        },

        show: {
            type: Boolean,
            default: undefined,
        },

        hugText: {
            type: Boolean,
            default: false,
        },

        title: {
            type: String,
            default: undefined,
        },

        placement: {
            type: String,
            default: 'right',
        },

        icon: {
            type: String,
            default: 'info',
        },

        boundary: {
            default: undefined,
        },
    },

    components: {
        Icon,
    },
};
</script>

<style lang="less">
.desc-pop-span {
    padding: 0 0.5em;
    height: 100%;
    display: inline-block;

    .description-popover.float-right & {
        padding-right: 0;
    }
}

.description-popover {
    display: inline;
    cursor: help;
}

.description-popover-content {
    text-align: justify;
    hyphens: auto;
}
</style>
