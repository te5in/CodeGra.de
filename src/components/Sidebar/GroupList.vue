<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="sidebar-list-wrapper">
    <ul class="sidebar-list"
        v-if="groupSets && groupSets.length > 0">
        <li v-for="groupSet in groupSets"
            :class="{
                      'sidebar-list-item': true,
                      'selected': $route.name === 'manage_groups' && groupSet.id === curGroupSetId,
                    }"
            >
            <router-link
                class="sidebar-item name"
                :to="{ name: 'manage_groups', params: { courseId: course.id, groupSetId: groupSet.id }, query: { sbloc: 'g' } }"
                >
                <span v-if="groupSet.assignment_ids.length === 0">
                    Unused group set
                </span>
                <span v-else>
                    Group set used by
                    {{ groupSet.assignment_ids.map(id => assignments[id] && assignments[id].name).join(', ') }}
                </span>
            </router-link>
        </li>
    </ul>
    <span v-else class="sidebar-list no-items-text">
        You don't have any group sets yet.
    </span>
</div>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';

import Icon from 'vue-awesome/components/Icon';

export default {
    name: 'group-list',

    props: {
        data: {
            type: Object,
            default: null,
        },
    },

    computed: {
        ...mapGetters('courses', ['assignments']),

        course() {
            return this.data.course;
        },

        curGroupSetId() {
            return Number(this.$route.params.groupSetId);
        },

        groupSets() {
            return this.course && this.course.group_sets;
        },
    },

    async mounted() {
        this.$root.$on('sidebar::reload', this.reload);
    },

    destroyed() {
        this.$root.$off('sidebar::reload', this.reload);
    },

    methods: {
        ...mapActions('courses', ['reloadCourses']),

        reload() {
            this.reloadCourses().then(() => {
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
@import '~mixins.less';

a {
    text-decoration: none;
    color: inherit;
    width: 100%;
    align-items: baseline;
}
</style>
