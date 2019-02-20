<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="inner-markdown-viewer">
    <div class="rendered markdown"
         :class="{'show-whitespace': showCodeWhitespace}"
         v-html="html"/>
</div>
</template>

<script>
import markdownIt from 'markdown-it';
import markdownItMathjax from 'markdown-it-mathjax';
import markdownItSanitizer from 'markdown-it-sanitizer';

import { highlightCode } from '@/utils';

const md = markdownIt({
    html: true,
    typographer: false,
    highlight(str, lang) {
        return highlightCode(str.split('\n'), lang).join('<br>');
    },
});
md.use(markdownItMathjax()).use(markdownItSanitizer);

export default {
    name: 'inner-markdown-viewer',

    props: {
        markdown: {
            type: String,
            required: true,
        },

        showCodeWhitespace: {
            type: Boolean,
            required: true,
        },
    },

    computed: {
        html() {
            return md.render(this.markdown);
        },
    },

    watch: {
        html: {
            async handler() {
                // Make sure html is rendered before we kick MathJax.
                await this.$nextTick();
                window.MathJax.Hub.Queue(['Typeset', window.MathJax.Hub, this.$el]);
            },
            immediate: true,
        },
    },
};
</script>

<style lang="less">
.inner-markdown-viewer {
    pre {
        margin-bottom: 0;
        font-size: 100%;
        white-space: pre-wrap;
        word-wrap: break-word;
        word-break: break-word;
        hyphens: auto;
    }
    .MathJax_SVG svg {
        max-width: 100%;
    }
}
</style>
