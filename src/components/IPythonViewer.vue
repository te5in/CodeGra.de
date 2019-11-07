<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="ipython-viewer p-3">
    <inner-ipython-viewer
        :assignment="assignment"
        :editable="editable"
        :submission="submission"
        :file-id="fileId"
        :output-cells="outputCells"
        :show-whitespace="showWhitespace"
        :without-feedback="!showInlineFeedback"
        :can-use-snippets="canUseSnippets"
        />
</div>
</template>

<script>
import { mapGetters, mapActions } from 'vuex';

import decodeBuffer from '@/utils/decode';
import { getOutputCells } from '@/utils/ipython';

import InnerIpythonViewer from './InnerIPythonViewer';

export default {
    name: 'ipython-viewer',

    props: {
        assignment: {
            type: Object,
            required: true,
        },
        submission: {
            type: Object,
            required: true,
        },
        file: {
            type: Object,
            default: null,
        },
        cells: {
            type: Array,
            default: () => [],
        },
        editable: {
            type: Boolean,
            required: false,
        },
        showWhitespace: {
            type: Boolean,
            required: true,
        },
        showInlineFeedback: {
            type: Boolean,
            default: true,
        },
        canUseSnippets: {
            type: Boolean,
            required: true,
        },
        invalidJsonMessage: {
            type: String,
            default: 'The file is not a valid IPython notebook.',
        },
    },

    data() {
        return {
            outputCells: this.cells,
        };
    },

    computed: {
        ...mapGetters('pref', ['fontSize']),

        fileId() {
            return (this.file && this.file.id) || this.file.ids[0] || this.file.ids[1];
        },

        feedback() {
            return this.$utils.getProps(this.submission, {}, 'feedback', 'user', this.fileId);
        },
    },

    methods: {
        ...mapActions('code', {
            storeLoadCode: 'loadCode',
        }),

        outputData(output, types) {
            for (let i = 0; i < types.length; ++i) {
                if (output.data[types[i]]) {
                    return output.data[types[i]];
                }
            }
            return null;
        },

        async loadCode() {
            this.outputCells = this.cells;
            if (this.fileId == null) {
                return;
            }

            let jsonString;
            await this.$afterRerender();

            try {
                const code = await this.storeLoadCode(this.fileId);
                jsonString = decodeBuffer(code);
            } catch (e) {
                this.outputCells = [];
                this.$emit('error', e);
                return;
            }

            try {
                const data = JSON.parse(jsonString);
                this.outputCells = Object.freeze(getOutputCells(data));
                this.$emit('load');
            } catch (e) {
                this.outputCells = [];
                this.$emit('error', this.invalidJsonMessage);
            }
        },
    },

    watch: {
        fileId: {
            immediate: true,
            handler() {
                this.loadCode();
            },
        },
    },

    components: {
        InnerIpythonViewer,
    },
};
</script>

<style lang="less" scoped>
.ipython-viewer {
    position: relative;
}
</style>
