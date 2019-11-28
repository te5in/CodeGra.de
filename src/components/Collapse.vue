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
        <div class="content" v-if="loaded">
            <slot/>
        </div>
    </component>
</component>
</template>

<script>
import Vue from 'vue';

const EVENT_TOGGLE = 'cg::toggle::collapse';
const EVENT_STATE = 'cg::toggle::state';
const BVT = '__CG_toggle__';

Vue.directive('cg-toggle', {
    bind(el, binding, vnode) {
        const target = binding.value;
        if (!target) {
            // eslint-disable-next-line
            console.warning('Target not given found!');
        }
        vnode.elm.addEventListener('click', () => {
            vnode.context.$root.$emit(EVENT_TOGGLE, target);
        });

        el.setAttribute('aria-controls', target);
        el.setAttribute('aria-expanded', 'false');
        if (el.tagName !== 'BUTTON') {
            // If element is not a button, we add `role="button"` for accessibility
            el.setAttribute('role', 'button');
        }

        el[BVT] = function toggleDirectiveHandler(id, state) {
            if (target != null && target === id) {
                // Set aria-expanded state
                el.setAttribute('aria-expanded', state ? 'true' : 'false');
                // Set/Clear 'collapsed' class state
                if (state) {
                    el.classList.remove('collapsed');
                    el.classList.remove('x-collapsed');
                } else {
                    el.classList.add('collapsed');
                    el.classList.add('x-collapsed');
                }
            }
        };
        vnode.context.$root.$on(EVENT_STATE, el[BVT]);
    },

    unbind(el, binding, vnode) {
        if (el[BVT]) {
            // Remove our $root listener
            vnode.context.$root.$off(EVENT_STATE, el[BVT]);
            el[BVT] = null;
        }
    },
});

export default {
    name: 'collapse',

    model: {
        prop: 'collapsed',
        event: 'change',
    },

    created() {
        this.$root.$on(EVENT_TOGGLE, this.handleToggleEvent);
    },

    beforeDestroy() {
        this.$root.$off(EVENT_TOGGLE, this.handleToggleEvent);
    },

    props: {
        id: {
            type: [String, Number],
            default: null,
        },

        collapsed: {
            type: Boolean,
            default: true,
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

        lazyLoad: {
            type: Boolean,
            default: false,
        },
    },

    data() {
        return {
            state: this.collapsed ? 'collapsed' : 'expanded',
            contentStyle: {
                height: this.collapsed ? '0px' : 'auto',
            },
            loaded: !this.lazyLoad || !this.collapsed,
            show: !this.collapsed,
        };
    },

    watch: {
        collapsed(newValue, oldValue) {
            if (newValue !== oldValue) {
                this.show = !newValue;
            }
        },

        show(newVal, oldVal) {
            if (newVal !== oldVal) {
                this.emitState();
                this.toggle();
            }
        },
    },

    mounted() {
        this.emitState();
    },

    methods: {
        handleToggleEvent(target) {
            if (this.id == null || target !== this.id || this.disabled) {
                return;
            }
            this.show = !this.show;
        },

        emitState() {
            this.$emit('change', !this.show);
            this.$root.$emit(EVENT_STATE, this.id, this.show);
        },

        onClick() {
            if (!this.disabled) {
                this.show = !this.show;
            }
        },

        setState(name) {
            this.state = name;
            this.$emit(name);
        },

        async toggle() {
            if (!this.loaded) {
                this.loaded = true;
                await this.$afterRerender();
            }

            const wrapperEl = this.$refs.content;
            const contentEl = wrapperEl.firstChild;
            const wrapperHeight = this.getHeight(wrapperEl);
            const contentHeight = this.getHeight(contentEl);
            const newHeight = this.show ? contentHeight : 0;
            const duration = this.getDuration(contentHeight);
            const transitionId = this.$utils.getUniqueId();

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
            await this.$afterRerender();

            this.contentStyle = {
                height: `${newHeight}px`,
                transitionDuration: `${duration}ms`,
            };

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
            if (!this.show) {
                this.toggle();
            }
        },

        collapse() {
            if (this.show) {
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
