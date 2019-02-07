<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="groups-management">
    <loader v-if="loading"/>
    <div v-else>
        <transition-group v-if="groups.length > 0"
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

        <p class="text-muted">
            <span v-if="groups.length === 0">
                There are no groups yet.
            </span>

            <span v-if="!showAddButton || !canCreate">
                <span v-if="currentUserInGroup">
                    You don't have the permission to create any new groups.
                </span>
                <span v-else>
                    You are currently not in a group and you don't have the permission to create any.
                </span>
                Please ask your instructor to create a group, if needed.

                <span v-if="groupSet.minimum_size > 1">
                    To submit work it is mandatory that you are in a group of at least
                    {{ groupSet.minimum_size }} members.
                </span>

                <span v-else>
                    You are not required to be part of a group to submit work for this assignment.
                </span>
            </span>
        </p>

        <div class="button-wrapper" v-if="showAddButton && canCreate">
            <submit-button label="Create new group" @click="addGroup" ref="addButton"/>
        </div>
    </div>
</div>
</template>

<script>
import { mapGetters } from 'vuex';

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
            canCreate: false,
        };
    },

    computed: {
        ...mapGetters('user', { myId: 'id' }),

        selectedMembers() {
            const res = new Set();
            this.groups.forEach(group => group.members.forEach(user => res.add(user.id)));
            return res;
        },

        currentUserInGroup() {
            return this.groups.some(group => group.members.some(user => user.id === this.myId));
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
                ['can_edit_own_groups', 'can_edit_others_groups', 'can_create_groups'],
                this.course.id,
            ).then(([own, others, create]) => {
                this.canEdit = { own, others };
                this.canCreate = create;
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

.group-management {
    margin-bottom: 1rem;
}

.button-wrapper {
    margin-top: 1rem;
    .btn {
        float: right;
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
