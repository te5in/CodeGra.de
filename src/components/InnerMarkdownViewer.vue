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

const makeMd = () =>
    markdownIt({
        html: true,
        typographer: false,
        highlight(str, lang) {
            return highlightCode(str.split('\n'), lang).join('<br>');
        },
    });
const md = makeMd();
const mdNoMath = makeMd();

md.use(markdownItMathjax()).use(markdownItSanitizer);
mdNoMath.use(markdownItSanitizer);

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
            if (this.disableMath) {
                return mdNoMath.render(this.markdown);
            } else {
                return md.render(this.markdown);
            }
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
