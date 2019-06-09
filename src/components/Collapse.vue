<template>
<div class="x-collapse" :class="className">
    <span class="handle" :class="{ disabled }" ref="handle" @click.stop="onClick">
        <slot name="handle"/>
    </span>

    <div class="content" ref="content" :style="contentStyle">
        <slot name="content"/>
    </div>
</div>
</template>

<script>
export default {
    name: 'collapse',

    model: {
        prop: 'collapsed',
        event: 'change',
    },

    props: {
        collapsed: {
            type: Boolean,
            default: false,
        },

        disabled: {
            type: Boolean,
            default: false,
        },

        speed: {
            type: Number,
            default: 1000,
        },
    },

    data() {
        return {
            className: this.collapsed ? 'x-collapsed' : 'x-expanded',
            contentStyle: {
                height: this.collapsed ? '0px' : 'auto',
            },
        };
    },

    watch: {
        collapsed(newValue, oldValue) {
            console.log('collapse changed from', oldValue, 'to', newValue, this.$el);
            if (newValue !== oldValue) {
                this.toggle();
            }
        },
    },

    methods: {
        onClick() {
            if (!this.disabled) {
                this.toggle();
                this.$emit('change', !this.collapsed);
            }
        },

        async toggle() {
            if (this.disabled) {
                return;
            }

            const wrapperEl = this.$refs.content;
            const contentEl = wrapperEl.firstChild;
            const wrapperHeight = this.getHeight(wrapperEl);
            const contentHeight = this.getHeight(contentEl);
            const newHeight = this.collapsed ? 0 : contentHeight;
            const duration = 1000 * contentHeight / this.speed;

            this.className = newHeight ? 'x-expanding' : 'x-collapsing';
            this.contentStyle = {
                height: `${wrapperHeight}px`,
                transitionDuration: `${duration}ms`,
            };

            await Promise.all([
                this.$nextTick(),
                new Promise(resolve => {
                    setTimeout(resolve, 10);
                }),
            ]);

            this.contentStyle = {
                height: `${newHeight}px`,
                transitionDuration: `${duration}ms`,
            };

            const onTransitionEnd = () => {
                wrapperEl.removeEventListener('transitionend', onTransitionEnd);

                this.className = newHeight ? 'x-expanded' : 'x-collapsed';
                this.contentStyle = {
                    height: newHeight ? 'auto' : '0px',
                };
            };

            wrapperEl.addEventListener('transitionend', onTransitionEnd);
        },

        expand() {
            if (this.collapsed) {
                this.toggle();
            }
        },

        collapse() {
            if (!this.collapsed) {
                this.collapse();
            }
        },

        getHeight(el) {
            const s = getComputedStyle(el);

            return [
                el.clientHeight,
                parseInt(s.marginTop, 10),
                parseInt(s.marginBottom, 10),
            ].reduce((x, y) => x + y);
        },
    },
};
</script>

<style lang="less" scoped>
.handle {
    &:not(.disabled) {
        cursor: pointer;
    }
}

.content {
    transition-property: height;
    overflow: hidden;
}
</style>
