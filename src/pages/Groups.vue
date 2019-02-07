<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<loader v-if="loading"/>
<div v-else class="groups">
    <local-header>
        <template slot="title">
            <span v-if="groupSet.assignment_ids.length === 0">
                Unused group set
            </span>
            <span v-else>
                Group set used by {{ formattedAssignments }}
            </span>
        </template>
        <b-form-fieldset class="filter-input">
            <input v-model="filter"
                   class="form-control"
                   placeholder="Type to search"/>
        </b-form-fieldset>

        <submit-button @click="reload"
                       variant="secondary"
                       ref="refreshButton"
                       :label="false"
                       v-b-popover.bottom.hover="'Reload groups'">
            <icon name="refresh"/>
            <icon name="refresh" spin slot="pending"/>
        </submit-button>
    </local-header>

    <div class="content">
        <groups-management :group-set="groupSet"
                           :course="course"
                           ref="groups"
                           :filter="filterGroup"/>
    </div>
</div>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';

import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/refresh';

import { nameOfUser, waitAtLeast } from '@/utils';

import GroupsManagement from '@/components/GroupsManagement';
import LocalHeader from '@/components/LocalHeader';
import Loader from '@/components/Loader';
import SubmitButton from '@/components/SubmitButton';

export default {
    name: 'groups-page',

    data() {
        return {
            loading: true,
            filter: '',
        };
    },

    watch: {
        groupSetId(newVal, oldVal) {
            if (newVal !== oldVal) {
                this.loadData();
            }
        },
    },

    computed: {
        ...mapGetters('courses', ['assignments', 'courses']),

        course() {
            return this.courses[this.courseId];
        },

        courseId() {
            return Number(this.$route.params.courseId);
        },

        groupSetId() {
            return Number(this.$route.params.groupSetId);
        },

        groupSet() {
            if (!this.course) {
                return null;
            }
            const set = this.course.group_sets.filter(s => this.groupSetId === s.id);
            return set.length > 0 ? set[0] : null;
        },

        formattedAssignments() {
            return this.groupSet.assignment_ids
                .map(id => this.assignments[id] && this.assignments[id].name)
                .filter(name => name != null)
                .join(', ');
        },
    },

    mounted() {
        this.loadData();
    },

    methods: {
        ...mapActions('courses', ['loadCourses', 'reloadCourses']),

        loadData() {
            this.loading = true;
            return waitAtLeast(250, this.loadCourses()).then(() => {
                this.loading = false;
            });
        },

        reload() {
            this.$refs.refreshButton.submit(
                waitAtLeast(250, this.$refs.groups.loadData(), this.reloadCourses()),
            );
        },

        filterGroup(group) {
            if (!this.filter) return true;

            const terms = [
                group.name,
                ...group.members.map(nameOfUser),
                ...group.members.map(u => u.username),
            ].map(t => t.toLowerCase());

            return this.filter
                .toLowerCase()
                .split(' ')
                .every(word => terms.some(term => term.indexOf(word) >= 0));
        },
    },

    components: {
        Icon,
        GroupsManagement,
        LocalHeader,
        Loader,
        SubmitButton,
    },
};
</script>

<style lang="less">
@import '~mixins.less';

.filter-input {
    flex: 1 1 auto;
    margin-bottom: 0;
}
</style>
