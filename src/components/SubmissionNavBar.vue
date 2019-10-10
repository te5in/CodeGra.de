<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<b-input-group class="submission-nav-bar">
    <b-button-group class="nav-wrapper">
        <b-button v-if="showUserButtons || filteredSubmissions.length > 1"
                  :disabled="prevSub == null"
                  v-b-popover.hover.bottom="generatePopoverTitle(prevSub)"
                  @click="selectSub(prevSub)">
            <icon name="angle-left"/>
        </b-button>

        <b-dropdown @show="onDropdownShow" v-if="curSub"
                    class="title navbar-old-subs-dropdown"
                    :class="subLate(curSub) ? 'current-sub-late' : ''">
            <template slot="button-content">
                <span class="button-content">
                    <user :user="curSub.user"/> at {{ curSub.formatted_created_at }}
                    <span class="d-inline-block" style="tranform: translateY(-2px)">
                        <late-submission-icon
                            :submission="curSub"
                            :assignment="assignment"/>
                    </span>
                    <icon name="exclamation-triangle"
                          class="text-warning ml-1"
                          style="margin-bottom: -1px;"
                          v-b-popover.top.hover="'You are currently not viewing the latest submission.'"
                          v-if="notLatest"/>
                </span>
            </template>
            <template v-if="!loadingOldSubs && oldSubmissions != null">
                <b-dropdown-item v-if="oldSubmissions.length === 0">
                    <b>No submissions found on the server</b>
                </b-dropdown-item>
                <b-dropdown-item v-for="sub in oldSubmissions"
                                 :key="sub.id"
                                 v-else
                                 href="#"
                                 @click="selectSub(sub)"
                                 :class="{currentSub: sub.id === curSub.id, 'sub-late': subLate(sub)}"
                                 class="old-sub">
                    {{ sub.formatted_created_at }}
                    <template v-if="sub.grade != null">
                        graded with a {{ sub.grade }}
                    </template>
                    <template v-if="sub === oldSubmissions[0]">
                        <i>(Newest version)</i>
                    </template>
                    <late-submission-icon
                        hide-popover
                        :submission="curSub"
                        :assignment="assignment"/>
                </b-dropdown-item>
            </template>
            <b-dropdown-item v-else>
                <loader :scale="1"
                        class="old-sub"
                        :center="true"/>
            </b-dropdown-item>
        </b-dropdown>

        <div class="title placeholder" v-else>
            -
        </div>
        <b-button v-if="showUserButtons || filteredSubmissions.length > 1"
                  :disabled="nextSub == null"
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
import { mapGetters, mapActions } from 'vuex';
import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/angle-left';
import 'vue-awesome/icons/exclamation-triangle';
import 'vue-awesome/icons/angle-right';

import User from './User';
import Loader from './Loader';
import LateSubmissionIcon from './LateSubmissionIcon';

export default {
    name: 'submission-nav-bar',

    props: {
        latestSubmissions: {
            type: Array,
            required: true,
        },

        currentSubmission: {
            type: Object,
            required: true,
        },

        notLatest: {
            type: Boolean,
            required: true,
        },

        showUserButtons: {
            type: Boolean,
            default: true,
        },

        assignment: {
            type: Object,
            required: true,
        },
    },

    data() {
        return {
            oldSubmissions: null,
            loadingOldSubs: false,
        };
    },

    watch: {
        curUserId() {
            this.oldSubmissions = null;
        },
    },

    computed: {
        ...mapGetters({
            userId: 'user/id',
        }),

        curUserId() {
            return this.curSub ? null : this.curSub.user.id;
        },

        curSub() {
            return this.currentSubmission;
        },

        loading() {
            return this.curSub == null;
        },

        assignmentId() {
            return this.assignment.id;
        },

        submissionId() {
            return Number(this.$route.params.submissionId);
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
            return this.filterSubmissionsManager.filter(this.latestSubmissions, {
                mine: this.filterAssignee,
                userId: this.userId,
                filter: this.filter,
                sortBy: this.sortBy,
                asc: this.sortAsc,
            });
        },

        optionIndex() {
            if (this.loading) {
                return null;
            }
            return this.filteredSubmissions.findIndex(sub => sub.user.id === this.curSub.user.id);
        },

        prevSub() {
            if (this.loading) {
                return null;
            }
            if (this.optionIndex > 0 && this.optionIndex < this.filteredSubmissions.length) {
                return this.filteredSubmissions[this.optionIndex - 1];
            }
            return null;
        },

        nextSub() {
            if (this.loading) {
                return null;
            }
            if (this.optionIndex >= 0 && this.optionIndex < this.filteredSubmissions.length - 1) {
                return this.filteredSubmissions[this.optionIndex + 1];
            }
            return null;
        },
    },

    methods: {
        ...mapActions('submissions', ['loadSingleSubmission', 'loadSubmissionsByUser']),

        subLate(sub) {
            return sub.formatted_created_at > this.assignment.formatted_deadline;
        },

        selectSub(sub) {
            if (sub == null) {
                return;
            } else if (sub.id === this.curSub.id) {
                return;
            }

            this.$router.push(
                this.$utils.deepExtend({}, this.$route, {
                    name: 'submission',
                    params: {
                        submissionId: sub.id,
                        fileId: undefined,
                    },
                    hash: undefined,
                }),
            );
        },

        async onDropdownShow() {
            const sub = this.curSub;
            if (this.oldSubmissions != null || sub == null) {
                return;
            }
            this.loadingOldSubs = true;
            const subs = await this.loadSubmissionsByUser({
                assignmentId: this.assignmentId,
                userId: sub.user.id,
            });

            if (this.curSub && this.curSub.id === sub.id) {
                this.oldSubmissions = subs;
                this.loadingOldSubs = false;
            }
        },

        generatePopoverTitle(sub) {
            return `Go to ${sub && nameOfUser(sub.user)}'s submission`;
        },
    },

    components: {
        Icon,
        User,
        Loader,
        LateSubmissionIcon,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';
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
    text-align: center;
    &.placeholder {
        background-color: white;
        border: 1px solid #ccc;
        padding: 0.375rem 0.75rem;
    }

    #app.dark & {
        background-color: @color-primary;
        border-color: @color-primary-darker;
    }
}

.old-sub {
    text-align: center;
}

.currentSub {
    background-color: @color-lighter-gray;

    #app:not(.lti).dark & {
        background-color: @color-primary-darkest;
    }
}
</style>

<style lang="less">
@import '~mixins.less';

.navbar-old-subs-dropdown {
    .btn {
        width: 100%;
        display: flex;
        align-items: center;

        .button-content {
            flex: 1 1 auto;
        }
    }
    .dropdown-menu {
        width: 100%;
        overflow: auto;
        padding: 0;
    }

    .sub-late,
    &.current-sub-late .dropdown-toggle {
        background-color: @color-danger-table-row !important;

        &:hover {
            background-color: saturate(darken(@color-danger-table-row, 5%), -20%) !important;
        }
    }
}
</style>
