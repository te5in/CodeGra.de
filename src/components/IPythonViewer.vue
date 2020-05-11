<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="ipython-viewer">
    <inner-ipython-viewer
        :assignment="assignment"
        :editable="editable"
        :submission="submission"
        :file-id="fileId"
        :output-cells="outputCells"
        :show-whitespace="showWhitespace"
        :without-feedback="!showInlineFeedback"
        :can-use-snippets="canUseSnippets" />
</div>
</template>

<script>
import { mapGetters } from 'vuex';

import decodeBuffer from '@/utils/decode';
import { getOutputCells, nbformatVersion } from '@/utils/ipython';

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
        fileId: {
            type: String,
            required: true,
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
        fileContent: {
            required: true,
        },
    },

    computed: {
        ...mapGetters('pref', ['fontSize']),
        feedback() {
            return this.$utils.getProps(this.submission, {}, 'feedback', 'user', this.fileId);
        },

        outputCells() {
            if (this.fileId == null || this.fileContent == null) {
                return [];
            }

            const error = err => {
                this.$emit('error', {
                    error: err,
                    fileId: this.fileId,
                });
                return [];
            };

            let jsonString;
            try {
                jsonString = decodeBuffer(this.fileContent);
            } catch (e) {
                return error(e);
            }

            let data;
            try {
                data = JSON.parse(jsonString);
            } catch (e) {
                return error(this.invalidJsonMessage);
            }

            if (nbformatVersion(data) === 3) {
                this.$emit('warning', new Error(
                    'Jupyter Notebook format v3 detected. May not render correctly.',
                ));
            }

            try {
                const res = Object.freeze(getOutputCells(data));
                this.$emit('load', this.fileId);
                return res;
            } catch (e) {
                return error(e);
            }
        },
    },

    methods: {
        outputData(output, types) {
            for (let i = 0; i < types.length; ++i) {
                if (output.data[types[i]]) {
                    return output.data[types[i]];
                }
            }
            return null;
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
