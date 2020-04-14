<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="categories">
    <div class="category align-self-stretch"
         :class="{selected: !disabled && cat.id === value}"
         v-for="cat in categories"
         v-if="cat.enabled"
         @click="processInput(cat.id, false)"
         :key="cat.id">
        <span class="name">
            {{ cat.name }}

            <!-- Bootstrap-Vue uses variant secondary when no variant is
                 given, so we can't use it here. -->
            <div v-if="cat.badge"
                 class="ml-1 badge"
                 :class="cat.badge.variant ? `badge-${cat.badge.variant}` : ''">
                {{ cat.badge.label }}
            </div>
        </span>
        <div class="indicator"/>
    </div>
</div>
</template>

<script>
export default {
    name: 'category-selector',

    props: {
        value: {
            type: String,
            required: true,
        },
        categories: {
            type: Array,
            required: true,
        },
        default: {
            type: String,
            required: true,
        },
        disabled: {
            type: Boolean,
            default: false,
        },
    },

    computed: {
        enabledCats() {
            return this.categories.filter(cat => cat.enabled);
        },
    },

    watch: {
        disabled() {
            if (!this.disabled) {
                this.$emit('input', this.getInitialValue());
            }
        },

        enabledCats: {
            immediate: true,
            handler() {
                this.$emit('input', this.getInitialValue());
            },
        },

        $route(newVal) {
            if (this.disabled) {
                return;
            }
            let val = decodeURI(newVal.hash && newVal.hash.slice(1)) || this.default;
            if (val !== this.value) {
                // Selected value is not available
                if (!this.enabledCats.find(x => x.id === val)) {
                    // Keep the same value
                    if (
                        this.enabledCats.find(x => x.id === this.value) ||
                        this.enabledCats.length === 0
                    ) {
                        val = this.value;
                    } else {
                        val = this.enabledCats[0];
                    }
                }
                this.processInput(val, true);
            }
        },
    },

    methods: {
        getInitialValue() {
            const hash = decodeURI(this.$route.hash && this.$route.hash.slice(1));
            if (hash) {
                return hash;
            }
            if (this.enabledCats.length === 0) {
                return this.default;
            }
            const hasDefault = this.enabledCats.filter(cat => cat.id === this.default).length > 0;
            if (hasDefault) {
                return this.default;
            }
            return this.enabledCats[0].id;
        },

        processInput(catId, forceEmit) {
            if (this.disabled) {
                return;
            }
            if (forceEmit || catId !== this.value) {
                this.$router.replace(
                    Object.assign({}, this.$route, {
                        hash: `#${catId || this.default}`,
                    }),
                );
                this.$emit('input', catId);
            }
        },
    },
};
</script>

<style lang="less">
@import '~mixins.less';

.categories {
    display: flex;
    flex-direction: row;
}

.category {
    flex: 1 1 auto;
    display: flex;
    flex-direction: column;
    line-height: 1rem;
    padding: 0 1rem;
    cursor: pointer;
    position: relative;

    .categories:last-child & {
        margin-bottom: -1rem;

        @media @media-small {
            margin-bottom: -0.8rem;
        }
    }

    .indicator {
        position: absolute;
        bottom: 0;
        border-bottom: 2px solid transparent;
        left: 12.5%;
        width: 75%;
        margin: 0 auto;
        transition: border-bottom-color 150ms;
    }

    &.selected .indicator {
        border-bottom: 2px solid @color-primary;

        @{dark-mode} {
            border-bottom: 2px solid @color-secondary;
        }
    }

    &:hover .indicator {
        &,
        @{dark-mode} {
            border-bottom: 2px solid lighten(@color-secondary, 20%);
        }
    }

    .name {
        text-align: center;
        padding-bottom: 0.25rem;
        padding: 0.5rem;
        font-size: 0.75rem;
    }

    .badge {
        text-transform: uppercase;
        vertical-align: super;
    }
}
</style>
