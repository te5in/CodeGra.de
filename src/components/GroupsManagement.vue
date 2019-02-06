<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="groups-management">
    <loader v-if="loading"/>
    <p v-else-if="!groups.length"
        class="text-center text-muted">
        No groups have been created yet.
    </p>
    <transition-group v-else
                      :name="doAnimations ? 'fade' : ''"
                      tag="div">
        <group-management v-for="group, i in groups"
                          :value="groups[i]"
                          @input="(val) => changedGroup(val, i)"
                          v-if="filter(group, i)"
                          :show-lti-progress="showLtiProgress(group, i)"
                          :can-edit-own="canEdit.own"
                          :can-edit-others="canEdit.others"
                          :selected-members="selectedMembers"
                          :key="`assignment-group-${group.id}`"
                          :assignment="assignment"
                          :course="course"
                          :group-set="groupSet"/>
    </transition-group>
    <div class="button-wrapper" v-if="showAddButton && (canEdit.own || canEdit.others)">
        <submit-button label="Create new group" @click="addGroup" ref="addButton"/>
    </div>
    <!-- This is showed on assignment pages-->
    <div v-if="!loading && !(showAddButton && (canEdit.own || canEdit.others)) && groups.length === 0"
         class="no-perms">
        You are currently in no group and you don't have the permission to
        create any. Please ask your instructor to add you to a group.
        <span v-if="groupSet.minimum_size > 1">
            To submit work it is mandatory that you are in a group of at least
            {{ groupSet.minimum_size }} members.
        </span>
        <span v-else>
            You are not required to be part of a group to submit work for this assignment.
        </span>
    </div>
</div>
</template>

<script>
import UserSelector from '@/components/UserSelector';
import GroupManagement from '@/components/GroupManagement';
import PermissionsManager from '@/components/PermissionsManager';
import LocalHeader from '@/components/LocalHeader';
import Loader from '@/components/Loader';
import Toggle from '@/components/Toggle';
import SubmitButton from '@/components/SubmitButton';

export default {
    name: 'groups-management',

    props: {
        groupSet: {
            type: Object,
            required: true,
        },

        course: {
            type: Object,
            required: true,
        },

        assignment: {
            type: Object,
            default: null,
        },

        filter: {
            type: Function,
            default: () => true,
        },

        showLtiProgress: {
            type: Function,
            default: () => false,
        },

        showAddButton: {
            type: Boolean,
            default: true,
        },
    },

    data() {
        return {
            groups: [],
            loading: true,
            doAnimations: false,
            canEdit: {
                own: false,
                others: false,
            },
        };
    },

    computed: {
        selectedMembers() {
            const res = new Set();
            this.groups.forEach(group => group.members.forEach(user => res.add(user.id)));
            return res;
        },
    },

    watch: {
        groupSet: {
            immediate: true,
            handler(newVal, oldVal) {
                if (!newVal || !oldVal || oldVal.id !== newVal.id) {
                    this.loadData();
                }
            },
        },

        async filter() {
            this.doAnimations = false;
            await this.$nextTick();
            this.doAnimations = true;
        },
    },

    methods: {
        loadData() {
            this.doAnimations = false;
            this.groups = [];
            this.loading = true;
            return Promise.all([this.getGroups(), this.getPermissions()]).then(() => {
                this.loading = false;
                this.$nextTick(() => {
                    this.doAnimations = true;
                });
            });
        },

        addGroup() {
            const req = this.$http
                .post(`/api/v1/group_sets/${this.groupSet.id}/group`, { member_ids: [] })
                .then(
                    ({ data }) => {
                        this.groups.push(data);
                    },
                    err => {
                        throw err.response.data.message;
                    },
                );
            this.$refs.addButton.submit(req);
        },

        getGroups() {
            return this.$http
                .get(`/api/v1/group_sets/${this.groupSet.id}/groups/`)
                .then(({ data }) => {
                    this.groups = [...data] || [];
                });
        },

        getPermissions() {
            return this.$hasPermission(
                ['can_edit_own_groups', 'can_edit_others_groups'],
                this.course.id,
            ).then(([own, others]) => {
                this.canEdit = { own, others };
            });
        },

        async changedGroup(group, index) {
            if (group === undefined) {
                this.groups.splice(index, 1);
                this.groups = this.groups;
            } else {
                this.$set(this.groups, index, group);
            }
            await this.$nextTick();
            this.$emit('groups-changed', [...this.groups]);
        },
    },

    components: {
        GroupManagement,
        UserSelector,
        PermissionsManager,
        LocalHeader,
        Loader,
        Toggle,
        SubmitButton,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.group-management:not(:last-child) {
    margin-bottom: 1rem;
}

.button-wrapper {
    margin-top: 1rem;
    .btn {
        float: right;
    }
}

.no-perms {
    color: gray;
    #app.dark & {
        color: @color-light-gray;
    }
}

.fade-enter-active,
.fade-leave-active {
    transition: opacity @transition-duration;
}
.fade-enter,
.fade-leave-to {
    opacity: 0;
}
</style>
