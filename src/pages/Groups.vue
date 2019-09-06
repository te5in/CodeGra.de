<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<loader v-if="loading"/>
<div v-else class="groups">
    <local-header :back-route="$utils.getProps(getPreviousRoute(), null, 'name') && getPreviousRoute()"
                  :back-popover="backPopover">
        <template slot="title">
            <span v-if="groupSet.assignment_ids.length === 0">
                Unused group set
            </span>
            <span v-else>
                Group set used by
                <span v-for="(assig, index) in groupAssignments">
                    <router-link
                        :to="getAssignmentLink(assig)"
                        class="inline-link"
                        >{{ assig.name }}</router-link
                                                      ><template
                                                           v-if="index + 1 < groupAssignments.length"
                                                           >,
                    </template>
                </span>
            </span>
        </template>
        <b-form-fieldset class="filter-input">
            <input v-model="filter"
                   class="form-control"
                   placeholder="Type to search"/>
        </b-form-fieldset>

        <submit-button :submit="reload"
                       variant="secondary"
                       v-b-popover.bottom.hover="'Reload groups'">
            <icon name="refresh"/>
            <icon name="refresh" spin slot="pending-label"/>
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

import { getPreviousRoute } from '@/router';

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
            getPreviousRoute,
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

        backPopover() {
            const prev = this.getPreviousRoute();
            if (prev == null || prev.name == null) {
                return '';
            }
            return `Go back to the ${prev.name.replace(/_/g, ' ')} page`;
        },

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

        groupAssignments() {
            return this.groupSet.assignment_ids
                .map(id => this.assignments[id])
                .filter(assig => this.$utils.getProps(assig, null, 'name') != null);
        },
    },

    mounted() {
        this.loadData();
    },

    methods: {
        ...mapActions('courses', ['loadCourses', 'reloadCourses']),

        getAssignmentLink(assig) {
            return {
                name: 'assignment_submissions',
                params: {
                    courseId: this.courseId,
                    assignmentId: assig.id,
                },
            };
        },

        loadData() {
            this.loading = true;
            return waitAtLeast(250, this.loadCourses()).then(() => {
                this.loading = false;
            });
        },

        reload() {
            return waitAtLeast(250, this.$refs.groups.loadData(), this.reloadCourses());
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
