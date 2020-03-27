<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template functional>
<span v-if="props.user.group"
      class="user"
      :title="props.showTitle ? props.getNameOfUser(props.user) : undefined">
    <span class="group-name">
        {{ props.beforeGroup }} "{{ props.user.group.name }}"
    </span>
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
                    <span v-if="props.showYou && member.id == props.getMyId()"
                          class="user-you-text">
                        (You)
                    </span>
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
    <span v-if="props.showWhenYou != null && props.user.id == props.getMyId()">
        {{ props.showWhenYou }}
    </span>
    <template v-else>
        <span class="name-user">
            {{ props.user.name || props.user.username }}
        </span>
        <span v-if="props.showYou && props.user.id === props.getMyId()"
            class="user-you-text">
            (You)
        </span>
    </template>
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
import { store } from '@/store';

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

        showWhenYou: {
            type: String,
            default: null,
        },

        showYou: {
            type: Boolean,
            default: false,
        },

        getMyId: {
            type: Function,
            default: () => store.getters['user/id'],
        },
    },
};
</script>

<style lang="less" scoped>
.user {
    display: inline-block;
    .user-you-text {
        font-style: italic;
    }
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
