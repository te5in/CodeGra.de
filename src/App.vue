<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div id="app" :class="{ dark: hasDarkMode, lti: $inLTI }">
    <sidebar ref="sidebar"
             v-if="showSidebar"/>
    <div class="container-fluid">
        <main class="row justify-content-center">
            <b-alert class="ie-banner"
                     :show="$root.isIE"
                     variant="warning"
                     dismissible>
                It seems the browser you are using is Internet Explorer which
                is not fully supported. We suggest you use another browser to get
                the most out of CodeGrade!
            </b-alert>
            <router-view class="page col-lg-12"/>
            <footer-bar v-if="showFooter"/>
        </main>
    </div>
</div>
</template>

<script>
import { FooterBar, Sidebar } from '@/components';

export default {
    name: 'app',

    computed: {
        hasDarkMode() {
            return this.$store.getters['pref/darkMode'];
        },

        showSidebar() {
            return this.$route.name !== 'lti-launch';
        },

        showFooter() {
            return (
                this.$route.name !== 'submission' &&
                this.$route.name !== 'submission_file' &&
                this.$route.name !== 'plagiarism_detail'
            );
        },
    },

    created() {
        if (this.$route.query.inLTI !== undefined) {
            this.$inLTI = true;
        }

        let popoversShown = false;

        document.body.addEventListener(
            'click',
            event => {
                popoversShown = false;
                if (!event.target.closest('.popover-body')) {
                    if (!event.target.closest('.sidebar') && this.$refs.sidebar) {
                        this.$refs.sidebar.$emit('sidebar::close');
                    }

                    setTimeout(() => {
                        this.$nextTick(() => {
                            if (!popoversShown) {
                                this.$root.$emit('bv::hide::popover');
                            }
                        });
                    }, 10);
                }
            },
            true,
        );

        this.$root.$on('bv::popover::show', () => {
            popoversShown = true;
        });

        document.body.addEventListener(
            'keyup',
            event => {
                if (event.key === 'Escape') {
                    this.$root.$emit('bv::hide::popover');
                }
            },
            true,
        );
    },

    components: {
        FooterBar,
        Sidebar,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

#app {
    display: flex;
    flex-direction: row;
    min-height: 100vh;
}

.container-fluid {
    display: flex;
    flex-grow: 1;

    .lti & {
    }

    main {
        position: relative;
        display: flex;
        flex-direction: column;
        flex: 1 1 auto;

        .default-background;
        .default-color;
    }

    .page {
        flex: 1 1 auto;
        margin-bottom: 1rem;
    }
}

.ie-banner {
    position: absolute;
    top: 1rem;
    left: 1rem;
    right: 1rem;
    z-index: 100;
}
</style>
