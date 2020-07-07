<template>
<div class="outline-viewer" :class="`outline-viewer-level-${level}`">
    <ol class="pl-0">
        <li v-for="option in options"
            :key="option.id">
            <a href="#"
               @click.prevent="$emit('goto-option', option)"
               class="d-block border-left"
               :class="{
                       'active': openOptions[option.id],
                       'not-active': !openOptions[option.id],
                       }"
               :style="{
                       'padding-left': `${0.5 + 1.5 * level}rem`,
                       }">
                <slot name="option"
                      :option="option"
                      :open="openOptions[option.id]"  />
            </a>
            <outline-viewer :options="option.children"
                            :level="level + 1"
                            @goto-option="$emit('goto-option', $event)"
                            :selected-option="selectedOption"
                            v-if="openOptions[option.id] && option.children" >
                <template #option="{ option, open }">
                    <slot name="option" :open="open" :option="option" />
                </template>
            </outline-viewer>
        </li>
    </ol>
</div>
</template>

<script lang="ts">
import { Vue, Component, Prop } from 'vue-property-decorator';

export type OutlineOption = {
    id: number | string;
    data?: any;
    children?: ReadonlyArray<OutlineOption>;
};

@Component
export default class OutlineViewer extends Vue {
    @Prop({ required: true }) options!: ReadonlyArray<OutlineOption>;

    @Prop({ required: true }) selectedOption!: string | number | null;

    @Prop({ default: 0 }) level!: number;

    get openOptions(): Record<number | string, boolean> {
        const selected = this.selectedOption;

        if (this.options.some(opt => opt.id === selected)) {
            return this.$utils.mapToObject(this.options, opt => [opt.id, opt.id === selected]);
        } else {
            const anyChild = (children: ReadonlyArray<OutlineOption>): boolean => children.some(
                c => {
                    if (c.id === selected) {
                        return true;
                    }
                    return anyChild(c.children ?? []);
                },
            );

            return this.$utils.mapToObject(
                this.options,
                opt => [opt.id, anyChild(opt.children ?? [])],
            );
        }
    }
}
</script>

<style lang="less" scoped>
@import '~mixins.less';

ol {
    list-style: none !important;
}

a {
    border-color: @color-primary !important;

    &.active {
        border-left-width: 3px !important;
    }

    &.not-active {
        margin-left: 2px;
    }
}
</style>
