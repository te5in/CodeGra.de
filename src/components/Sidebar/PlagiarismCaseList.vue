<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="plagiarism-case-list sidebar-list-wrapper">
    <div class="sidebar-filter">
        <input class="form-control"
               placeholder="Filter courses"
               v-model="filter"
               ref="filter">
    </div>

    <ul class="sidebar-list" v-if="cases.length > 0">
        <li v-for="curCase in filteredCases"
            :class="{ 'light-selected': curCase.id ===  plagiarismCaseId }"
            class="sidebar-list-item">
            <router-link class="sidebar-item name"
                         :to="caseRoute(curCase)">
                <div class="name-user" style="width: 100%">
                    {{ curCase.users[0].name }}
                </div>
                <div style="display: flex;">
                    <div class="name-user" style="flex: 0 1 auto; margin-right: 5px">
                        {{ curCase.users[1].name }}
                    </div>
                    <div>
                        <sup v-b-popover.hover.top="getOtherAssignmentPlagiarismDesc(curCase, 1)"
                                                     v-if="curCase.assignments[1].id != run.assignment.id"
                                                     class="description"
                                                     >*</sup>
                    </div>
                </div>
                <small style="display: block; line-height: 1.3em">
                    Avg. match: {{ curCase.match_avg.toFixed(0) }}% &ndash;
                    Max. match: {{ curCase.match_max.toFixed(0) }}%
                </small>
            </router-link class="sidebar-item">
        </li>
    </ul>
    <span v-else class="sidebar-list no-items-text">
        No plagiarism cases found
    </span>
</div>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';
import { getOtherAssignmentPlagiarismDesc } from '@/utils';

import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/plus';


export default {
    name: 'plagiarism-case-list',

    props: {
        data: {
            type: Object,
            default: null,
        },
    },

    data() {
        return {
            filter: '',
            getOtherAssignmentPlagiarismDesc,
        };
    },

    computed: {
        ...mapGetters('plagiarism', ['runs']),

        plagiarismRunId() {
            return `${this.$route.params.plagiarismRunId}`;
        },

        plagiarismCaseId() {
            return Number(this.$route.params.plagiarismCaseId);
        },

        run() {
            return this.runs[this.plagiarismRunId];
        },

        cases() {
            return (this.run && this.run.cases) || [];
        },

        filteredCases() {
            if (!this.filter) {
                return this.cases;
            }

            const filterParts = this.filter.toLocaleLowerCase().split(' ');

            return this.cases.filter(
                curCase => filterParts.every((part) => {
                    if (curCase.users[0].name.toLocaleLowerCase().indexOf(part) > -1) {
                        return true;
                    }
                    if (curCase.users[1].name.toLocaleLowerCase().indexOf(part) > -1) {
                        return true;
                    }
                    if (curCase.match_avg.toFixed(2).toLocaleLowerCase().indexOf(part) > -1) {
                        return true;
                    }
                    return curCase.match_max.toFixed(2).toLocaleLowerCase().indexOf(part) > -1;
                }),
            );
        },
    },

    async mounted() {
        this.$root.$on('sidebar::reload', this.reload);

        if (this.run == null) {
            await this.reload();
        }

        await this.$nextTick();
        const activeEl = document.activeElement;
        if (!activeEl ||
            !activeEl.matches('input, textarea') ||
            activeEl.closest('.sidebar .submenu')) {
            this.$refs.filter.focus();
        }
    },

    destroyed() {
        this.$root.$off('sidebar::reload', this.reload);
    },

    methods: {
        ...mapActions('plagiarism', ['refreshRun']),

        caseRoute(curCase) {
            return {
                name: 'plagiarism_detail',
                params: {
                    courseId: this.run.assignment.course.id,
                    assignmentId: this.run.assignment.id,
                    plagiarismRunId: this.run.id,
                    plagiarismCaseId: curCase.id,
                },
            };
        },

        reload() {
            this.$emit('loading');
            return this.refreshRun(this.plagiarismRunId).then(() => {
                this.$emit('loaded');
            });
        },
    },

    components: {
        Icon,
    },
};
</script>

<style lang="less" scoped>
@import "~mixins.less";

a {
    text-decoration: none;
    color: inherit;
    max-width: 100%;
    width: 100%;
    align-items: baseline;
    .name-user {
        white-space: nowrap;
        text-overflow: ellipsis;
        line-height: 1.5em;
        overflow-x: hidden;
    }
}
</style>
