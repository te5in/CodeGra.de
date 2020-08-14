<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="finished-grader-toggles">
    <table class="table table-striped"
            v-if="internalGraders">
        <thead>
            <tr>
                <th>Grader</th>
                <th/>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
            <tr v-for="grader, i in internalGraders"
                :key="grader.userId"
                class="grader">
                <td><user :user="getUser(grader.userId)"/></td>
                <td class="shrink">
                    <b-popover placement="top"
                               :show="!!(warningGraders[grader.userId] || errorGraders[grader.userId])"
                               :target="`grader-icon-${assignment.id}-${grader.userId}`">
                        <span v-if="errorGraders[grader.userId]">
                            {{ errorGraders[grader.userId] }}
                        </span>
                        <span v-else>
                            {{ warningGraders[grader.userId] }}
                        </span>
                    </b-popover>

                    <icon :name="iconStyle(grader.userId)"
                          :spin="!(errorGraders[grader.userId] || warningGraders[grader.userId])"
                          :id="`grader-icon-${assignment.id}-${grader.userId}`"
                          :class="iconClass(grader.userId)"
                          :style="{
                              opacity: warningGraders[grader.userId] ||
                                           loadingGraders[grader.userId] ||
                                           errorGraders[grader.userId] ? 1 : 0,
                          }"/>
                </td>
                <td class="shrink">
                    <toggle label-on="Done"
                            label-off="Grading"
                            :disabled="!canUpdateOthers && $store.getters['user/id'] != grader.userId"
                            v-model="grader.done"
                            disabled-text="You cannot change the grader status of other graders"
                            @input="toggleGrader(grader)"/>
                </td>
        </tr>
        </tbody>
    </table>
    <span v-else>No graders found for this assignment</span>
</div>
</template>

<script>
import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/times';
import 'vue-awesome/icons/circle-o-notch';
import 'vue-awesome/icons/exclamation-triangle';
import { mapGetters } from 'vuex';
import { WarningHeader, waitAtLeast } from '@/utils';

import * as models from '@/models';

import Toggle from './Toggle';
import User from './User';

export default {
    props: {
        assignment: {
            type: Object,
            required: true,
        },

        graders: {
            type: Array,
            required: true,
        },
    },

    data() {
        return {
            internalGraders: [],
            loadingGraders: {},
            errorGraders: {},
            warningGraders: {},
        };
    },

    computed: {
        ...mapGetters('users', ['getUser']),

        permissions() {
            return new models.AssignmentCapabilities(this.assignment);
        },

        canUpdateOthers() {
            return this.permissions.canUpdateOtherGraderStatus;
        },
    },

    mounted() {
        this.internalGraders = this.graders.map(g => Object.assign({}, g));
    },

    methods: {
        iconClass(graderId) {
            if (this.errorGraders[graderId]) {
                return 'text-danger';
            } else if (this.warningGraders[graderId]) {
                return 'text-warning';
            }
            return '';
        },
        iconStyle(graderId) {
            if (this.errorGraders[graderId]) {
                return 'times';
            } else if (this.warningGraders[graderId]) {
                return 'exclamation-triangle';
            }
            return 'circle-o-notch';
        },
        toggleGrader(grader) {
            const { userId } = grader;
            this.$set(this.warningGraders, userId, undefined);
            delete this.warningGraders[userId];
            this.$set(this.loadingGraders, userId, true);

            let req;

            if (grader.done) {
                req = this.$http.post(
                    `/api/v1/assignments/${this.assignment.id}/graders/${userId}/done`,
                );
            } else {
                req = this.$http.delete(
                    `/api/v1/assignments/${this.assignment.id}/graders/${userId}/done`,
                );
            }

            waitAtLeast(500, req)
                .then(
                    res => {
                        if (res.headers.warning) {
                            const warning = WarningHeader.fromResponse(res);
                            this.$set(
                                this.warningGraders,
                                userId,
                                warning.messages.map(w => w.text).join(' '),
                            );
                            this.$nextTick(() =>
                                setTimeout(() => {
                                    this.$set(this.warningGraders, userId, undefined);
                                    delete this.warningGraders[userId];
                                }, 2000),
                            );
                        }
                    },
                    err => {
                        this.$set(this.errorGraders, userId, err.response.data.message);

                        this.$nextTick(() =>
                            setTimeout(() => {
                                grader.done = !grader.done;

                                this.$set(this.errorGraders, userId, undefined);
                                delete this.errorGraders[userId];
                            }, 2000),
                        );
                    },
                )
                .then(() => {
                    this.$set(this.loadingGraders, userId, undefined);
                    delete this.loadingGraders[userId];
                });
        },
    },

    components: {
        Icon,
        Toggle,
        User,
    },
};
</script>

<style lang="less" scoped>
.table {
    margin-bottom: 0;
}

.table th {
    border-top: none;
}

.table th:last-child {
    text-align: center;
}

.table td:not(:first-child) {
    padding: 0.5rem;
}

.table td:nth-child(2) {
    padding-top: 0.75rem;
}
</style>
