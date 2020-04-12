<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="manage-course">
    <local-header always-show-extra-slot>
        <b-form-fieldset class="filter-input">
            <input v-model="filter"
                    class="form-control"
                    placeholder="Type to Search"/>
        </b-form-fieldset>

        <template slot="extra">
            <category-selector
                v-if="course"
                slot="extra"
                class="cat-selector"
                v-model="selectedCat"
                default="members"
                :categories="categories"/>
        </template>
    </local-header>

    <loader v-if="!course" page-loader/>
    <div class="content" v-else>
        <users-manager :class="{ hidden: selectedCat !== 'members'}"
                       class="cat-wrapper"
                       v-if="membersEnabled"
                       :course="course"
                       :filter="filter"/>
        <permissions-manager :class="{ hidden: selectedCat !== 'permissions' }"
                             v-if="permissionsEnabled"
                             class="cat-wrapper"
                             :course-id="course.id"
                             :filter="filter"/>
        <span :class="{ hidden: selectedCat !== 'groups' }"
              v-if="groupsEnabled"
              class="cat-wrapper">
            <group-set-manager :course="course"/>
        </span>

        <span :class="{ hidden: selectedCat !== 'snippets' }"
              class="cat-wrapper">
            <snippet-manager
                v-if="snippetsEnabled"
                :course="course"
                :editable="course.permissions.can_manage_course_snippets"/>
        </span>

        <div :class="{ hidden: selectedCat !== 'contact' }"
              class="cat-wrapper">
            <b-form-group>
                <label>Recipients</label>
                <user-selector placeholder="Students to email"
                           v-model="usersToEmail"
                           :use-selector="canListUsers"
                           :base-url="`/api/v1/courses/${course.id}/users/`"
                           multiple />
            </b-form-group>

            <student-contact
                :submit="sendEmail"
                :course="course"
                :default-subject="defaultEmailSubject"
                no-cancel
                @emailed="usersToEmail = []"
                :can-use-snippets="canUseSnippets"/>
        </div>
    </div>
</div>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';

import { TaskResult } from '@/models';

import UsersManager from '@/components/UsersManager';
import PermissionsManager from '@/components/PermissionsManager';
import LocalHeader from '@/components/LocalHeader';
import Loader from '@/components/Loader';
import CategorySelector from '@/components/CategorySelector';
import GroupSetManager from '@/components/GroupSetManager';
import SnippetManager from '@/components/SnippetManager';
import UserSelector from '@/components/UserSelector';
import StudentContact from '@/components/StudentContact';

import { setPageTitle } from './title';

export default {
    name: 'manage-course-page',

    data() {
        return {
            selectedCat: '',
            filter: '',
            usersToEmail: [],
        };
    },

    computed: {
        ...mapGetters('courses', ['courses']),
        ...mapGetters('user', {
            userPerms: 'permissions',
        }),

        course() {
            return this.courses[this.$route.params.courseId];
        },

        courseId() {
            return Number(this.$route.params.courseId);
        },

        membersEnabled() {
            return this.course && this.course.permissions.can_edit_course_users;
        },

        permissionsEnabled() {
            return this.course && this.course.permissions.can_edit_course_roles;
        },

        groupsEnabled() {
            return (
                UserConfig.features.groups &&
                this.course &&
                this.course.permissions.can_edit_group_set
            );
        },

        snippetsEnabled() {
            return (
                this.course &&
                (this.course.permissions.can_manage_course_snippets ||
                    this.course.permissions.can_view_course_snippets)
            );
        },

        contactEnabled() {
            return (
                UserConfig.features.email_students &&
                    this.$utils.getProps(this.course, false, 'permissions', 'can_email_students')
            );
        },

        categories() {
            return [
                {
                    id: 'members',
                    name: 'Members',
                    enabled: this.membersEnabled,
                },
                {
                    id: 'permissions',
                    name: 'Permissions',
                    enabled: this.permissionsEnabled,
                },
                {
                    id: 'groups',
                    name: 'Groups',
                    enabled: this.groupsEnabled,
                },
                {
                    id: 'snippets',
                    name: 'Snippets',
                    enabled: this.snippetsEnabled,
                },
                {
                    id: 'contact',
                    name: 'Contact students',
                    enabled: this.contactEnabled,
                },
            ];
        },

        canListUsers() {
            const perms = this.$utils.getProps(this.course, {}, 'permissions');
            return !!(perms.can_list_course_users);
        },

        defaultEmailSubject() {
            return `An email about the "${this.course.name}" course on CodeGrade`;
        },

        canUseSnippets() {
            return !!this.userPerms.can_use_snippets;
        },
    },

    async mounted() {
        await this.loadCourses();
    },

    watch: {
        course() {
            setPageTitle(this.course.name);
        },
    },

    methods: {
        ...mapActions('courses', ['loadCourses']),

        sendEmail(subject, body) {
            const usernames = this.usersToEmail.map(u => u.username).filter(u => u !== '' && u != null);
            if (usernames.length === 0) {
                throw new Error('You have to select at least one recipient.');
            }

            return this.$http.post(`/api/v1/courses/${this.course.id}/email`, {
                subject,
                body,
                usernames,
            }).then(response => (
                {
                    ...response,
                    cgResult: new TaskResult(response.data.id),
                }
            ));
        },
    },

    components: {
        UsersManager,
        UserSelector,
        PermissionsManager,
        LocalHeader,
        Loader,
        CategorySelector,
        GroupSetManager,
        SnippetManager,
        StudentContact,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.manage-course {
    display: flex;
    flex-direction: column;
}
.manage-course > .content {
    flex: 1 1 auto;
    display: flex;
    flex-direction: column;
}

.filter-input {
    flex: 1 1 auto;
    margin-bottom: 0;
}

.cat-wrapper {
    transition: opacity @transition-duration ease-out;
    height: 100%;
    padding-top: 5px;

    &.hidden {
        height: 0;
        overflow: hidden;
        padding: 0;
        transition: none;
        opacity: 0;
        max-height: 0;
    }
}
</style>
