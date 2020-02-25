<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<loader v-if="loading"/>
<div v-else
     class="grade-history">
    <b-table striped
             :items="history"
             :fields="fields"
             show-empty
             empty-text="No grade history">
        <template #cell(user)="data">
            <user v-if="data.item.origin === 'human'"
                  :user="data.item.user"/>
            <i v-else
               v-b-popover.top.hover="'This grade was not given by a human.'">
                {{ convertGradeOrigin(data.item.origin) }}
            </i>
        </template>

        <template #cell(grade)="data">
            {{ data.item.grade >= 0 ? $utils.toMaxNDecimals(data.item.grade, 2) : 'Deleted' }}
        </template>

        <template #cell(rubric)="data">
            <icon :name="data.item.is_rubric ? 'check' : 'times'" />
        </template>

        <template v-if="isLTI"
                  #cell(lti)="data">
            <icon :name="data.item.passed_back ? 'check' : 'times'" />
        </template>
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

    mounted() {
        this.updateHistory();
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
    max-height: 40em;
    overflow-y: auto;
}

.table {
    margin-bottom: 0;
    cursor: text !important;
}
</style>

<style lang="less">
.grade-history .table {
    th,
    td {
        &:last-child {
            width: 1px;
            white-space: nowrap;
        }
    }
}
</style>
