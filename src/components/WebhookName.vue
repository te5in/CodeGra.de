<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template functional>
    <i v-if="props.gitOrigins[props.submission.origin]" class="webhook-name git">
        via
        <a :href="props.getGitLink(props.submission)"
           target="_blank"
           @click.stop
           class="inline-link"
           >{{ props.gitOrigins[props.submission.origin] }}</a>
        <component :is="injections.components.DescriptionPopover"
                   hug-text
                   triggers="click blur"
                   v-if="props.submission.extra_info">
            This submission was submitted through {{ props.gitOrigins[props.submission.origin] }}
            by <code>{{ props.submission.extra_info.sender_name }}</code>
            to the branch
            <code>{{ props.submission.extra_info.branch}}</code>.
            This is commit
            <code>{{ props.submission.extra_info.commit.slice(0, 7) }}</code>.
        </component>
    </i>
</template>

<script>
import DescriptionPopover from './DescriptionPopover';

export default {
    name: 'webhook-name',

    inject: {
        components: {
            default: {
                DescriptionPopover,
            },
        },
    },

    props: {
        submission: {
            type: Object,
            required: true,
        },

        getGitLink: {
            type: Function,
            default: sub => {
                const info = sub.extra_info;
                if (info == null) {
                    return undefined;
                }
                return `${info.url}/tree/${info.commit}`;
            },
        },

        gitOrigins: {
            type: Object,
            default: () => ({
                github: 'GitHub',
                gitlab: 'GitLab',
            }),
        },
    },
};
</script>
