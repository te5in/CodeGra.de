<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template functional>
    <span v-if="props.user.group" class="user">
        Group "{{ props.user.group.name }}"
        <component :is="injections.components.DescriptionPopover" hug-text triggers="click" boundary="window">
            <template slot="description" v-if="props.user.group.members.length">
                <span v-if="props.user.group.members.length === 1">
                    The group has only one member: {{ props.user.group.members[0].name }}
                </span>
                <span v-else>The members of this group are:
                <ul style="margin-bottom: 0; padding-left: 1rem;">
                    <li v-for="member in props.user.group.members">
                        {{ member.name }}
                    </li>
                </ul>
                </span>
            </template>
            <template slot="description" v-else>
                This group has no members.
            </template>
        </component>
    </span>
    <span v-else class="user">{{ props.user.name }}</span>
</template>

<script>
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
</style>
