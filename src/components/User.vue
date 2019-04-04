<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template functional>
    <span v-if="props.user.group" class="user">
        Group "{{ props.user.group.name }}"
        <component :is="injections.components.DescriptionPopover"
                   triggers="click"
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
    <span v-else class="user">{{ props.user.name }}</span>
</template>

<script>
import 'vue-awesome/icons/user-plus';

import DescriptionPopover from './DescriptionPopover';

export default {
    name: 'user',

    inject: {
        components: {
            default: {
                DescriptionPopover,
            },
        },
    },

    props: {
        user: {
            type: Object,
            required: true,
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
