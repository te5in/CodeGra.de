<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<loader v-if="loading"/>
<div class="grade-history" v-else>
    <b-table striped :items="history" :fields="fields" show-empty empty-text="No grade history">
        <template slot="user" slot-scope="data">
            <user v-if="data.item.origin === 'human'" :user="data.item.user"/>
            <span v-else><i v-b-popover.top.hover="'This grade was not given by a human.'"
                            >{{ convertGradeOrigin(data.item.origin) }}</i></span>
        </template>
        <span slot="grade" slot-scope="data">
            {{ data.item.grade >= 0 ? Math.round(data.item.grade * 100) / 100 : 'Deleted' }}
        </span>
        <span slot="rubric" slot-scope="data">
            <icon :name="data.item.is_rubric ? 'check' : 'times'" />
        </span>
        <span v-if="isLTI" slot="lti" slot-scope="data">
            <icon :name="data.item.passed_back ? 'check' : 'times'" />
        </span>
    </b-table>
</div>
</template>

<script>
import moment from 'moment';
import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/bars';
import Loader from './Loader';
import User from './User';

export default {
    name: 'grade-history',

    props: {
        showText: {
            type: String,
            default: 'Show grade history',
        },
        hideText: {
            type: String,
            default: 'Hide grade history',
        },
        submissionId: {
            type: Number,
            default: 0,
        },
        isLTI: {
            type: Boolean,
            default: false,
        },
    },

    data() {
        const fields = [
            {
                key: 'user',
                label: 'Grader',
            },
            {
                key: 'grade',
                label: 'Grade',
            },
            {
                key: 'changed_at',
                label: 'Date',
            },
            {
                key: 'rubric',
                label: 'By rubric',
            },
        ];
        if (this.isLTI) {
            fields.push({ key: 'lti', label: 'In LTI' });
        }
        return {
            history: [],
            fields,
            loading: false,
        };
    },

    methods: {
        updateHistory() {
            this.loading = true;
            const req = this.$http.get(`/api/v1/submissions/${this.submissionId}/grade_history/`);
            return req.then(({ data }) => {
                for (let i = 0, len = data.length; i < len; i += 1) {
                    data[i].changed_at = moment
                        .utc(data[i].changed_at, moment.ISO_8601)
                        .local()
                        .format('YYYY-MM-DD HH:mm');
                }
                this.history = data;
                this.loading = false;
            });
        },

        convertGradeOrigin(origin) {
            return {
                auto_test: 'AutoTest',
                human: 'Human',
            }[origin];
        },
    },

    components: {
        Icon,
        Loader,
        User,
    },
};
</script>

<style lang="less" scoped>
.grade-history {
    width: 30em;
    margin: -0.5rem -0.75rem;
    max-height: 40em;
    overflow-y: auto;
}

.table {
    margin-bottom: 0;
    cursor: text !important;

    th,
    td {
        padding: 0.25rem !important;
    }
}
</style>
