<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="assignment-group">
    <table class="range-table table table-striped table-hover">
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
                <td>
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
            </tr>
        </tbody>
    </table>

    <submit-button ref="submitButton" @click="submit"/>
</div>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';

import { waitAtLeast } from '@/utils';

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
                hash: '#Groups',
            };
        },

        assignmentUrl() {
            return `/api/v1/assignments/${this.assignment.id}`;
        },

        groupSets() {
            return this.assignment.course.group_sets;
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
            const btn = this.$refs.submitButton;
            const props = { group_set_id: null };

            if (this.selected) {
                props.group_set_id = this.selected;
            }
            const req = this.$http.patch(this.assignmentUrl, props).then(
                ({ data }) => {
                    const newSet = data.group_set || {};
                    const oldSet = this.assignment.group_set || {};

                    this.updateAssignment({
                        assignmentId: this.assignment.id,
                        assignmentProps: { group_set: newSet },
                    });
                    this.updateCourse({
                        courseId: this.assignment.course.id,
                        courseProps: {
                            group_sets: this.assignment.course.group_sets.map(set => {
                                if (set.id === newSet.id) {
                                    return newSet;
                                } else if (set.id === oldSet.id) {
                                    set.assignment_ids = set.assignment_ids.filter(
                                        id => id !== this.assignment.id,
                                    );
                                }
                                return set;
                            }),
                        },
                    });
                },
                err => {
                    throw err.response.data.message;
                },
            );

            btn.submit(waitAtLeast(500, req));
        },

        selectGroupSet(id) {
            this.selected = this.selected === id ? null : id;
        },
    },

    components: {
        SubmitButton,
        DescriptionPopover,
        Toggle,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.submit-button {
    margin-right: 1rem;
    float: right;
}

.group-table {
    vertical-align: middle;

    td:first-child:not(:last-child) {
        width: 1px;
        white-space: nowrap;
    }

    .toggle-container {
        padding: 0.375rem 0.5rem;
    }
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
