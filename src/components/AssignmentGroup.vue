<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="assignment-group">
    <table class="range-table table table-striped"
           :class="{ 'table-hover': groupSets.length > 0 }">
        <tbody class="group-table"
               name="fade"
               is="transition-group">
            <tr v-if="groupSets.length === 0"
                :key="-2">
                <td colspan="2">
                    There are no group sets for this course, they can be created
                    <router-link :to="manageLink" class="inline-link">here</router-link>.
                </td>
            </tr>
            <tr v-else
                v-for="groupSet in groupSets"
                :key="groupSet.id"
                @click.prevent="selectGroupSet(groupSet.id)">
                <td class="pr-0 shrink">
                    <b-form-checkbox @click.native.prevent
                                     :checked="selected === groupSet.id"/>
                </td>
                <td>
                    <ul>
                        <li>Minimum size: {{ groupSet.minimum_size }}, maximum size: {{ groupSet.maximum_size }}</li>
                        <li v-if="getOtherAssignmentIds(groupSet).length === 0">
                            Not used for other assignments
                        </li>
                        <li v-else>
                            Used for other assignments: {{ getFormattedOtherAssignment(groupSet) }}
                        </li>
                    </ul>
                </td>
                <td class="shrink">
                    <b-button :to="manageGroupsLink(groupSet)"
                              variant="primary"
                              size="sm"
                              v-b-popover.hover="'Manage groups in this set.'">
                        <icon name="pencil"/>
                    </b-button>
                </td>
            </tr>
        </tbody>
    </table>

    <b-button-toolbar justify
                      class="mx-1 px-2 py-3">
        <b-button :to="manageLink"
                  variant="outline-primary"
                  v-b-popover.hover.top="'Manage group sets for this course.'">
            Edit group sets
        </b-button>

        <div v-b-popover.hover.top="submitDisabledMessage">
            <submit-button v-if="groupSets.length > 0"
                           :disabled="!!submitDisabledMessage"
                           :submit="submit"
                           @success="afterSubmit"/>
        </div>
    </b-button-toolbar>
</div>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';

import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/pencil';

import SubmitButton from './SubmitButton';
import DescriptionPopover from './DescriptionPopover';
import Toggle from './Toggle';

export default {
    name: 'assignment-group',

    props: {
        assignment: {
            type: Object,
            default: null,
        },
    },

    computed: {
        ...mapGetters('courses', ['assignments']),

        manageLink() {
            return {
                name: 'manage_course',
                params: {
                    course_id: this.assignment.course.id,
                },
                hash: '#groups',
            };
        },

        assignmentUrl() {
            return `/api/v1/assignments/${this.assignment.id}`;
        },

        groupSets() {
            return this.assignment.course.group_sets;
        },

        submitDisabledMessage() {
            if (this.assignment.peer_feedback_settings == null) {
                return '';
            }
            return `This assignment has peer feedback enabled, but peer feedback
                is not yet supported for group assignments.`;
        },
    },

    data() {
        const gs = this.assignment.group_set;
        return {
            selected: gs && gs.id,
        };
    },

    methods: {
        ...mapActions('courses', ['updateAssignment', 'updateCourse']),

        getOtherAssignmentIds(groupSet) {
            return groupSet.assignment_ids.filter(id => this.assignment.id !== id);
        },

        getFormattedOtherAssignment(groupSet) {
            const assigIds = this.getOtherAssignmentIds(groupSet);
            return assigIds
                .map(id => this.assignments[id] && this.assignments[id].name)
                .filter(name => name != null)
                .join(', ');
        },

        toNumber(number) {
            const str = number.toString();
            if (/^[0-9]+$/.test(str)) {
                return parseInt(str, 10);
            } else {
                return null;
            }
        },

        submit() {
            const props = {
                group_set_id: this.selected || null,
            };

            return this.$http.patch(this.assignmentUrl, props);
        },

        afterSubmit(response) {
            const newSet = response.data.group_set || null;
            const oldSet = this.assignment.group_set || {};

            this.updateAssignment({
                assignmentId: this.assignment.id,
                assignmentProps: { group_set: newSet },
            });

            this.updateCourse({
                courseId: this.assignment.course.id,
                courseProps: {
                    group_sets: this.assignment.course.group_sets.map(set => {
                        if (newSet != null && set.id === newSet.id) {
                            return newSet;
                        } else if (set.id === oldSet.id) {
                            return Object.assign({}, set, {
                                assignment_ids: set.assignment_ids.filter(
                                    id => id !== this.assignment.id,
                                ),
                            });
                        }
                        return set;
                    }),
                },
            });
        },

        manageGroupsLink(groupSet) {
            return {
                name: 'manage_groups',
                params: {
                    courseId: this.assignment.course.id,
                    groupSetId: groupSet.id,
                },
            };
        },

        selectGroupSet(id) {
            this.selected = this.selected === id ? null : id;
        },
    },

    components: {
        SubmitButton,
        DescriptionPopover,
        Toggle,
        Icon,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.table {
    margin-bottom: 0;
}

.group-table {
    vertical-align: middle;
}

.fade-enter-active,
.fade-leave-active {
    transition: opacity @transition-duration;
}
.fade-enter,
.fade-leave-to {
    opacity: 0;
}

ul {
    margin: 0;
    list-style: none;
    padding: 0;
}

td {
    vertical-align: middle;
}
</style>
