<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
    <div class="pdf-viewer">
        <loader v-if="loading"/>
        <object :data="pdfURL"
                type="application/pdf"
                width="100%"
                height="100%"
                v-else-if="pdfURL !== ''">
            <b-alert variant="danger" :show="true">
                Your browser doesn't support the PDF viewer. Please download
                the PDF <a class="alert-link" :href="pdfURL">here</a>.
            </b-alert>
        </object>
        <b-alert variant="danger"
                 :show="error !== ''">
            {{ error }}
        </b-alert>
    </div>
</template>

<script>
import Loader from './Loader';

export default {
    name: 'pdf-viewer',

    props: {
        file: {
            type: Object,
            default: null,
        },

        isDiff: {
            type: Boolean,
            required: true,
        },
    },

    data() {
        return {
            pdfURL: '',
            loading: true,
            error: '',
        };
    },

    watch: {
        id() {
            this.embedPdf();
        },
    },

    computed: {
        id() {
            return this.file ? this.file.id : -1;
        },
    },

    mounted() {
        this.embedPdf();
    },

    methods: {
        embedPdf() {
            this.loading = true;
            this.error = '';
            this.pdfURL = '';

            if (this.isDiff) {
                this.error = 'The pdf viewer is not available in diff mode';
                this.loading = false;
                return;
            }

            this.$http.get(`/api/v1/code/${this.id}?type=file-url`).then(
                ({ data }) => {
                    this.loading = false;
                    this.$emit('load');
                    this.pdfURL = `/api/v1/files/${
                        data.name
                    }?not_as_attachment&mime=application/pdf`;
                },
                ({ response }) => {
                    this.error = `An error occurred while loading the PDF: ${
                        response.data.message
                    }.`;
                    this.loading = false;
                },
            );
        },
    },

    components: {
        Loader,
    },
};
</script>

<style lang="less" scoped>
.pdf-viewer {
    position: relative;
}

object {
    position: absolute;
    width: 100%;
    height: 100%;
}
</style>
