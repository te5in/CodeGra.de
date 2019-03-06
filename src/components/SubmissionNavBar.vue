<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<b-input-group class="submission-nav-bar">
    <b-button-group class="nav-wrapper">
        <b-button :disabled="prevSub == null"
                  v-b-popover.hover.bottom="generatePopoverTitle(prevSub)"
                  @click="selectSub(prevSub)">
            <icon name="angle-left"/>
        </b-button>
        <div class="title">
            <span v-if="curSub">
                Submission by <user :user="curSub.user"/>
            </span>
            <span v-else>
                -
            </span>
        </div>
        <b-button :disabled="nextSub == null"
                  v-b-popover.hover.bottom="generatePopoverTitle(nextSub)"
                  @click="selectSub(nextSub)">
            <icon name="angle-right"/>
        </b-button>
    </b-button-group>
</b-input-group>
</template>

<script>
import { parseBool, nameOfUser } from '@/utils';
import FilterSubmissionsManager from '@/utils/FilterSubmissionsManager';
import { mapGetters } from 'vuex';
import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/angle-left';
import 'vue-awesome/icons/angle-right';

import User from './User';

export default {
    name: 'submission-nav-bar',

    computed: {
        ...mapGetters('courses', ['assignments']),
        ...mapGetters({
            userId: 'user/id',
        }),

        assignmentId() {
            return Number(this.$route.params.assignmentId);
        },

        assignment() {
            return this.assignments[this.assignmentId];
        },

        submissionId() {
            return Number(this.$route.params.submissionId);
        },

        submissions() {
            return (this.assignment && this.assignment.submissions) || [];
        },

        latestOnly() {
            return parseBool(this.$route.query.latest, true);
        },

        filterAssignee() {
            return parseBool(this.$route.query.mine, true);
        },

        sortBy() {
            return this.$route.query.sortBy || 'user';
        },

        filter() {
            return this.$route.query.search;
        },

        sortAsc() {
            return parseBool(this.$route.query.sortAsc);
        },

        filterSubmissionsManager() {
            return new FilterSubmissionsManager(
                this.submissionId,
                this.$route.query.forceInclude,
                this.$route,
                this.$router,
            );
        },

        filteredSubmissions() {
            return this.filterSubmissionsManager.filter(this.submissions, {
                latest: this.latestOnly,
                mine: this.filterAssignee,
                userId: this.userId,
                filter: this.filter,
                sortBy: this.sortBy,
                asc: this.sortAsc,
            });
        },

        optionIndex() {
            return this.filteredSubmissions.findIndex(sub => sub.id === this.submissionId);
        },

        curSub() {
            return (this.submissions && this.filteredSubmissions[this.optionIndex]) || null;
        },

        prevSub() {
            if (this.optionIndex > 0 && this.optionIndex < this.filteredSubmissions.length) {
                return this.filteredSubmissions[this.optionIndex - 1];
            }
            return null;
        },

        nextSub() {
            if (this.optionIndex >= 0 && this.optionIndex < this.filteredSubmissions.length - 1) {
                return this.filteredSubmissions[this.optionIndex + 1];
            }
            return null;
        },
    },

    methods: {
        selectSub(sub) {
            if (sub == null) {
                return;
            }
            this.$router.push({
                params: Object.assign({}, this.$route.params, {
                    submissionId: sub.id,
                }),
                query: this.$route.query,
            });
        },

        generatePopoverTitle(sub) {
            return `Go to ${sub && nameOfUser(sub.user)}'s submission`;
        },
    },

    components: {
        Icon,
        User,
    },
};
</script>

<style lang="less" scoped>
.local-header {
    flex: 1 1 auto;
}

.select {
    border-left: 0;
    border-right: 0;
}

.slot {
    margin-left: 15px;
}

.nav-wrapper {
    flex: 1 1 auto;
}
</style>

<style lang="less">
@import '~mixins.less';

.submission-nav-bar .dropdown button {
    width: 100%;
    font-size: 1rem;
    padding: 0.5rem;
}

.dropdown-header .dropdown-item:active {
    background-color: inherit;
}

#student-selector {
    border-radius: 0;
    width: 100%;
    padding-top: 0.625rem;
}

.nav-wrapper .title {
    .default-text-colors;

    flex: 1;
    background-color: white;
    border: 1px solid #ccc;
    text-align: center;
    padding: 0.375rem 0.75rem;

    #app.dark & {
        background-color: @color-primary;
        border-color: @color-primary-darker;
    }
}
</style>
