<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="submisssions-sidebar-list sidebar-list-wrapper">
    <div class="sidebar-filter">
        <input class="form-control"
               placeholder="Filter submissions"
               v-model="filter"
               @keyup.enter="submit"
               ref="filter">
    </div>

    <ul class="sidebar-list" v-if="sortedFilteredSubmissions.length > 0">
        <li v-for="sub in sortedFilteredSubmissions"
            :class="{ 'light-selected': sub.id ===  submissionId }"
            :tabindex="0"
            @keyup.enter="gotoSub(sub)"
            class="sidebar-list-item">
            <a class="sidebar-item name"
               @click="gotoSub(sub)">
                {{ sub.user.name }}

                <small>
                    Created at: {{ sub.created_at }}
                </small>
                <small v-if="sub.assignee">
                    Assignee: {{ sub.assignee.name }}
                </small>
                <small>
                    Grade: {{ sub.grade === null ? '-' : sub.grade }}
                </small>
            </a>
        </li>
    </ul>
    <span v-else class="sidebar-list no-items-text">
        No submissions cases found
    </span>
</div>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';
import { parseBool } from '@/utils';
import FilterSubmissionsManager from '@/utils/FilterSubmissionsManager';

import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/plus';


export default {
    name: 'submissions-sidebar-list',

    props: {
        data: {
            type: Object,
            default: null,
        },
    },

    data() {
        return {
            filter: this.$route.query.search,
            submitTimeout: null,
        };
    },

    computed: {
        ...mapGetters('courses', ['assignments']),
        ...mapGetters({
            userId: 'user/id',
        }),

        assignmentId() {
            return Number(this.$route.params.assignmentId);
        },

        assignment() {
            return this.assignments[this.assignmentId];
        },

        submissionId() {
            return Number(this.$route.params.submissionId);
        },

        submissions() {
            return (this.assignment && this.assignment.submissions) || [];
        },

        latestOnly() {
            return parseBool(this.$route.query.latest, true);
        },

        filterAssignee() {
            return parseBool(this.$route.query.mine, true);
        },

        sortBy() {
            return this.$route.query.sortBy || 'user';
        },

        filterSubmissionsManager() {
            return new FilterSubmissionsManager(
                this.submissionId,
                this.$route.query.forceInclude,
                this.$route,
                this.$router,
            );
        },

        sortedFilteredSubmissions() {
            return this.filterSubmissionsManager.filter(
                this.submissions,
                this.latestOnly,
                this.filterAssignee,
                this.userId,
                this.filter,
                this.sortBy,
            );
        },
    },

    async mounted() {
        this.$root.$on('sidebar::reload', this.reload);

        await this.reload(false);

        await this.$nextTick();
        const activeEl = document.activeElement;
        if (!activeEl ||
            !activeEl.matches('input, textarea') ||
            activeEl.closest('.sidebar .submenu')) {
            this.$refs.filter.focus();
        }
    },

    watch: {
        filter() {
            this.submitDelayed();
        },
    },

    destroyed() {
        this.$root.$off('sidebar::reload', this.reload);
    },

    methods: {
        ...mapActions('courses', ['loadSubmissions', 'forceLoadSubmissions']),

        submit() {
            if (this.submitTimeout != null) {
                clearTimeout(this.submitTimeout);
                this.submitTimeout = null;
            }

            this.$router.replace({
                query: Object.assign({}, this.$route.query, {
                    search: this.filter || undefined,
                }),
            });
        },

        submitDelayed() {
            if (this.submitTimeout != null) {
                clearTimeout(this.submitTimeout);
            }

            this.submitTimeout = setTimeout(this.submit, 200);
        },

        async gotoSub(sub) {
            this.submit();
            await this.$nextTick();

            this.$router.push({
                params: Object.assign(
                    {},
                    this.$route.params,
                    { submissionId: sub.id },
                ),
                query: this.$route.query,
            });
            this.$emit('close-menu');
        },

        async reload(force = true) {
            this.$emit('loading');
            if (force) {
                await this.forceLoadSubmissions(this.assignmentId);
            } else {
                await this.loadSubmissions(this.assignmentId);
            }

            this.$emit('loaded');
            await this.$nextTick();

            let el = this.$el.querySelector('.sidebar-list .sidebar-list-item.light-selected');
            if (el) {
                for (let i = 0; i < 2; i++) {
                    if (!el.previousSibling) {
                        break;
                    }
                    el = el.previousSibling;
                }
                el.scrollIntoView(true);
            }
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
