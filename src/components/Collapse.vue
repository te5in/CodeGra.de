<template>
<div class="x-collapse" :class="`x-${state}`">
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

        maxDuration: {
            type: Number,
            default: 750,
        },
    },

    data() {
        return {
            state: this.collapsed ? 'collapsed' : 'expanded',
            contentStyle: {
                height: this.collapsed ? '0px' : 'auto',
            },
        };
    },

    watch: {
        collapsed(newValue, oldValue) {
            if (newValue !== oldValue) {
                this.toggle();
            }
        },
    },

    methods: {
        onClick() {
            if (!this.disabled) {
                this.$emit('change', !this.collapsed);
            }
        },

        setState(name) {
            this.state = name;
            this.$emit(name);
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
            const duration = Math.min(1000 * contentHeight / this.speed, this.maxDuration);

            this.setState(newHeight ? 'expanding' : 'collapsing');

            this.contentStyle = {
                height: `${wrapperHeight}px`,
                transitionDuration: `${duration}ms`,
            };

            // Wait until height/transisionDuration have been applied.
            await Promise.all([
                this.$nextTick(),
                new Promise(resolve => setTimeout(resolve, 10)),
            ]);

            this.contentStyle = {
                height: `${newHeight}px`,
                transitionDuration: `${duration}ms`,
            };

            const transitionId = this.$utils.getUniqueId();
            this.transitionId = transitionId;

            const comp = this;
            wrapperEl.addEventListener('transitionend', function onTransitionEnd() {
                wrapperEl.removeEventListener('transitionend', onTransitionEnd);

                if (this.transitionId === transitionId) {
                    comp.setState(newHeight ? 'expanded' : 'collapsed');
                    comp.contentStyle = {
                        height: newHeight ? 'auto' : '0px',
                    };
                }
            });
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
