<template>
<div class="advanced-collapse">
    <div class="mt-3 mb-2 d-flex flex-row justify-content-between">
        <div v-b-toggle="id"
             class="collapse-toggle align-self-center text-muted font-italic">
            <icon name="caret-down" class="mr-2" />
            {{ name }}
        </div>

        <slot name="toggle" />
    </div>

    <b-collapse :id="id"
                class="advanced-collapse"
                v-model="state">
        <slot />
    </b-collapse>
</div>
</template>

<script>
import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/caret-down';

export default {
    name: 'advanced-collapse',

    props: {
        name: {
            type: String,
            default: 'Advanced options',
        },
    },

    data() {
        return {
            id: `${this.$utils.getUniqueId()}`,
            state: false,
        };
    },

    components: {
        Icon,
    },
};
</script>

<style lang="less">
.collapse-toggle {
    cursor: pointer;

    .fa-icon {
        transition: transform 250ms linear;
    }

    .x-collapsing .handle .fa-icon,
    .x-collapsed .handle .fa-icon,
    &.collapsed .fa-icon {
        transform: rotate(-90deg);
    }
}
</style>
