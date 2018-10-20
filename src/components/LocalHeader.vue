<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="local-header">
    <b-button-toolbar class="toolbar" justify>
        <b-input-group-prepend style="cursor: pointer;"
                               v-if="backRoute || $root.$isSmallWindow">
            <b-button-group>
                <b-btn variant="primary"
                       class="sidebar-toggle"
                       @click="toggleSidebar()">
                    <icon name="bars"/>
                </b-btn>
                <b-btn :to="backRoute"
                       v-if="backRoute"
                       class="back-button"
                       v-b-popover.bottom.hover="backPopover">
                    <icon name="arrow-left"/>
                </b-btn>
            </b-button-group>
        </b-input-group-prepend>

        <slot v-show="$slots.title" name="prepend"/>

        <h4 v-if="title || $slots.title" class="title">
            <slot v-if="$slots.title" name="title">{{ title }}</slot>
            <span v-else>{{ title }}</span>
        </h4>

        <slot/>

        <b-input-group-append v-if="hasExtraSlot"
                              class="extra-button"
                              v-b-popover.bottom.hover="`${showExtra ? 'Hide' : 'Show'} more options`">
            <b-button v-b-toggle.local-header-extra
                      @click="showExtra = !showExtra">
                <icon name="angle-double-up" v-if="showExtra"/>
                <icon name="angle-double-down" v-else/>
            </b-button>
        </b-input-group-append>
    </b-button-toolbar>

    <b-collapse id="local-header-extra" v-if="hasExtraSlot">
        <hr class="separator">
        <slot name="extra"/>
    </b-collapse>
</div>
</template>

<script>
import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/angle-double-down';
import 'vue-awesome/icons/angle-double-up';
import 'vue-awesome/icons/arrow-left';
import 'vue-awesome/icons/bars';

export default {
    name: 'local-header',

    props: {
        title: {
            type: String,
            default: '',
        },

        forceExtraDrawer: {
            type: [Boolean, undefined],
            default: undefined,
        },

        backRoute: {
            type: Object,
            default: null,
        },

        backPopover: {
            type: String,
            default: 'Go back',
        },
    },

    computed: {
        hasExtraSlot() {
            if (this.forceExtraDrawer !== undefined) {
                return this.forceExtraDrawer;
            }
            return !!this.$slots.extra;
        },
    },

    data() {
        return {
            showExtra: false,
        };
    },

    methods: {
        toggleSidebar() {
            this.$root.$emit('sidebar::show');
        },
    },

    components: {
        Icon,
    },
};
</script>

<style lang="less" scoped>
@import "~mixins.less";

.local-header {
    position: sticky;
    top: 0;
    z-index: 3;
    margin: 0 -15px 1rem;
    border: 0;
    padding: 1rem;
    .default-footer-colors;
    box-shadow: 0 0 4px rgba(0, 0, 0, .75);
    color: @text-color;
}

@media @media-no-small {
    .sidebar-toggle {
        display: none;
    }

    .back-button {
        border-top-left-radius: .25rem !important;
        border-bottom-left-radius: .25rem !important;
    }
}

.title {
    flex: 2;
    margin-bottom: 0;
    text-align: left;
}

.toolbar {
    flex: 1 0 auto;
    align-items: center;
}

.separator {
    margin: 1em 0;
    border-color: @color-border-gray;

    #app.dark & {
        border-color: @color-primary-darkest;
    }
}
</style>

<style lang="less">
.local-header > .toolbar {
    & > * {
        margin-right: 1rem;
    }
    & > *:last-child {
        margin-right: 0;
    }
}
</style>
