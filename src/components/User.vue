<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template functional>
<span v-if="props.user.group"
      class="user"
      :title="props.showTitle ? props.getNameOfUser(props.user) : undefined">
    {{ props.beforeGroup }} "{{ props.user.group.name }}"
    <component :is="injections.components.DescriptionPopover"
               triggers="click blur"
               hug-text
               span-title="Click to show the users of this group"
               boundary="window"
               title="Group members"
               icon="user-plus">
        <template slot="description" v-if="props.user.group.members.length">
            <ul class="users-list">
                <li v-for="member in props.user.group.members">
                    <span class="name-user">{{ member.name }}</span>
                </li>
            </ul>
        </template>
        <template slot="description" v-else>
            This group has no members.
        </template>
    </component>
</span>
<span v-else
      class="user"
      :title="props.showTitle ? props.getNameOfUser(props.user) : undefined">
    {{ props.user.name || props.user.username }}
    <span v-if="props.user.is_test_student">
        <component
            :is="injections.components.Icon"
            name="warning"
            class="ml-2"
            v-b-popover.top.hover="'This student is a test student.'"/>
    </span>
</span>
</template>

<script>
import 'vue-awesome/icons/user-plus';
import 'vue-awesome/icons/warning';
import Icon from 'vue-awesome/components/Icon';
import { nameOfUser } from '@/utils';

import DescriptionPopover from './DescriptionPopover';

export default {
    name: 'user',

    inject: {
        components: {
            default: {
                DescriptionPopover,
                Icon,
            },
        },
    },

    props: {
        user: {
            type: Object,
            required: true,
        },
        beforeGroup: {
            type: String,
            default: 'Group',
        },
        showTitle: {
            type: Boolean,
            default: false,
        },

        getNameOfUser: {
            type: Function,
            default: nameOfUser,
        },
    },
};
</script>

<style lang="less" scoped>
.user {
    display: inline-block;
}

.name-user {
    white-space: nowrap;
}

.users-list {
    margin-bottom: 0;
    padding-left: 1rem;
    margin-left: 0;
}
</style>
