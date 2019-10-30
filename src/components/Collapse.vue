<template>
<component :is="wrapperTag"
           class="x-collapse"
           :class="`x-${state}`">
    <component :is="handleTag"
               class="handle"
               :class="{ disabled }"
               @click.stop="onClick">
        <slot name="handle"/>
    </component>

    <component :is="contentTag"
               class="content-wrapper"
               ref="content"
               :style="contentStyle">
        <div class="content">
            <slot/>
        </div>
    </component>
</component>
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

        minDuration: {
            type: Number,
            default: 250,
        },

        maxDuration: {
            type: Number,
            default: 750,
        },

        wrapperTag: {
            type: String,
            default: 'div',
        },

        handleTag: {
            type: String,
            default: 'div',
        },

        contentTag: {
            type: String,
            default: 'div',
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
            const wrapperEl = this.$refs.content;
            const contentEl = wrapperEl.firstChild;
            const wrapperHeight = this.getHeight(wrapperEl);
            const contentHeight = this.getHeight(contentEl);
            const newHeight = this.collapsed ? 0 : contentHeight;
            const duration = this.getDuration(contentHeight);

            if (contentHeight === 0) {
                // Collapse is not visible, so don't bother animating.
                this.contentStyle = { height: this.collapsed ? 0 : 'auto' };
                return;
            }

            this.setState(newHeight ? 'expanding' : 'collapsing');

            this.contentStyle = {
                height: `${wrapperHeight}px`,
                transitionDuration: `${duration}ms`,
            };

            // Wait until style has been applied.
            await Promise.all([this.$nextTick(), new Promise(resolve => setTimeout(resolve, 10))]);

            this.contentStyle = {
                height: `${newHeight}px`,
                transitionDuration: `${duration}ms`,
            };

            const transitionId = this.$utils.getUniqueId();
            this.transitionId = transitionId;

            const onTransitionEnd = () => {
                wrapperEl.removeEventListener('transitionend', onTransitionEnd);

                if (this.transitionId === transitionId) {
                    this.setState(newHeight ? 'expanded' : 'collapsed');
                    this.contentStyle = {
                        height: newHeight ? 'auto' : '0px',
                    };
                }
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

        getDuration(height) {
            let duration = 1000 * height / this.speed;

            duration = Math.min(duration, this.maxDuration);
            duration = Math.max(duration, this.minDuration);

            return duration;
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

.content-wrapper {
    transition-property: height;
    overflow: hidden;

    .content {
        overflow: auto;
    }
}
</style>

<style lang="less">
@import '~mixins.less';
.x-collapse {
    .toggle .fa-icon,
    .toggle.fa-icon {
        margin-right: 0.5rem;
        transition: transform @transition-duration;
    }

    &.x-collapsing > .handle,
    &.x-collapsed > .handle {
        .toggle .fa-icon,
        .toggle.fa-icon {
            transform: rotate(-90deg);
        }
    }
}
</style>
