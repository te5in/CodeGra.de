<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="submissions-exporter clearfix">
    <b-form-fieldset>
        <b-input-group>
            <b-input-group-prepend is-text>
                Filename
            </b-input-group-prepend>
            <input v-model="userFilename"
                   class="form-control"
                   type="text"
                   :placeholder="filename"/>
        </b-input-group>
    </b-form-fieldset>

    <b-form-fieldset
        label="Columns:"
        description="Checked columns will be included in the exported file.">
        <b-form-checkbox v-for="(col, key) in columns"
                            :key="key"
                            v-model="col.enabled">
            {{ col.name }}
        </b-form-checkbox>
    </b-form-fieldset>

    <b-form-fieldset
        label="Rows:"
        description="When <i>All</i> is selected all submissions of this
            assignment will be exported.<br>The <i>Current</i> option only
            exports the submissions that are shown by the current filter that
            is applied to the list.">
        <b-form-radio-group v-model="exportSetting">
            <b-form-radio value="All">All</b-form-radio>
            <b-form-radio value="Current">Current</b-form-radio>
        </b-form-radio-group>
    </b-form-fieldset>

    <submit-button variant="primary"
                   class="export-button"
                   label="Export as CSV"
                   :submit="createCSV"
                   @success="afterCreateCSV" />
</div>
</template>

<script>
import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/cog';

import Baby from 'babyparse';

import { downloadFile, nameOfUser } from '@/utils';

import SubmitButton from './SubmitButton';

export default {
    name: 'submissions-exporter',

    components: {
        Icon,
        SubmitButton,
    },

    props: {
        getSubmissions: {
            type: Function,
            required: true,
        },
        filename: {
            type: String,
            default: 'export.csv',
        },
        assignmentId: {
            type: Number,
            default: 0,
            required: true,
        },
        columns: {
            type: Array,
            default() {
                const cols = [
                    {
                        name: 'Id',
                        enabled: false,
                        getter: submission => submission.user.id,
                    },
                    {
                        name: 'Username',
                        enabled: true,
                        getter: submission => submission.user.username,
                    },
                    {
                        name: 'Name',
                        enabled: true,
                        getter: submission => nameOfUser(submission.user),
                    },
                    {
                        name: 'Grade',
                        enabled: true,
                        getter: submission => submission.grade,
                    },
                    {
                        name: 'Created at',
                        enabled: true,
                        getter: submission => submission.formatted_created_at,
                    },
                    {
                        name: 'Assigned to',
                        enabled: true,
                        getter: submission => nameOfUser(submission.assignee),
                    },
                    {
                        name: 'General feedback',
                        enabled: false,
                        getter: submission =>
                            this.$utils.getProps(submission, '', 'feedback', 'general'),
                    },
                    {
                        name: 'Line feedback',
                        enabled: false,
                        getter: submission =>
                            this.$utils.getProps(submission, [], 'feedback', 'user').join('\n'),
                    },
                ];

                if (UserConfig.features.linters) {
                    cols.push({
                        name: 'Linter feedback',
                        enabled: false,
                        getter: submission =>
                            this.$utils.getProps(submission, [], 'feedback', 'linter').join('\n'),
                    });
                }

                return cols;
            },
        },
    },

    computed: {
        items() {
            return this.exportSetting === 'All'
                ? this.getSubmissions(false)
                : this.getSubmissions(true);
        },

        enabledColumns() {
            return this.columns.filter(col => col.enabled);
        },

        currentFilename() {
            return encodeURIComponent(this.userFilename ? this.userFilename : this.filename);
        },
    },

    data() {
        return {
            exportSetting: 'Current',
            userFilename: null,
        };
    },

    methods: {
        createCSV() {
            const data = [];
            const idx = Object.keys(this.enabledColumns);
            let cont;

            if (this.enabledColumns.find(item => item.name.endsWith('feedback')) === undefined) {
                cont = Promise.resolve({ data: {} });
            } else {
                cont = this.$http.get(`/api/v1/assignments/${this.assignmentId}/feedbacks/`);
            }

            return cont.then(({ data: feedback }) => {
                for (let i = 0; i < this.items.length; i += 1) {
                    const item = Object.assign({}, this.items[i], {
                        feedback: feedback[this.items[i].id],
                    });
                    const row = {};
                    for (let j = 0; j < idx.length; j += 1) {
                        const col = this.enabledColumns[idx[j]];
                        row[col.name] = col.getter(item);
                    }
                    data.push(row);
                }
                const csv = Baby.unparse({
                    fields: this.enabledColumns.map(obj => obj.name),
                    data,
                });

                return { data: csv, filename: this.currentFilename };
            });
        },

        afterCreateCSV({ data, filename }) {
            downloadFile(data, filename, 'text/csv');
        },
    },
};
</script>

<style lang="less" scoped>
.export-button {
    float: right;
}
</style>
