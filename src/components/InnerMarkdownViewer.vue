<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="inner-markdown-viewer">
    <div class="rendered markdown"
         :class="{'show-whitespace': showCodeWhitespace}"
         v-html="html"/>
</div>
</template>

<script>
import { CgMarkdownIt } from '@/cg-math';
import markdownItSanitizer from 'markdown-it-sanitizer';

const md = new CgMarkdownIt();

md.use(markdownItSanitizer);

export default {
    name: 'inner-markdown-viewer',

    props: {
        markdown: {
            type: String,
            required: true,
        },

        showCodeWhitespace: {
            type: Boolean,
            default: true,
        },

        disableMath: {
            type: Boolean,
            default: false,
        },
    },

    computed: {
        html() {
            return md.render(this.markdown, this.disableMath);
        },
    },

    watch: {
        html: {
            async handler() {
                if (!this.disableMath) {
                    // Make sure html is rendered before we kick MathJax.
                    await this.$nextTick();
                    window.MathJax.Hub.Queue(['Typeset', window.MathJax.Hub, this.$el]);
                }
            },
            immediate: true,
        },
    },
};
</script>

<style lang="less">
.inner-markdown-viewer {
    pre {
        margin-bottom: 1rem;
        font-size: 100%;
        white-space: pre-wrap;
        word-wrap: break-word;
        word-break: break-word;
        hyphens: auto;
        margin-left: 1.5rem;
    }
    .MathJax_SVG svg {
        max-width: 100%;
    }
}
</style>
