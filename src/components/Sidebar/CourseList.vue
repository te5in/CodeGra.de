<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="course-list sidebar-list-wrapper">
    <div class="sidebar-filter">
        <input class="form-control"
               placeholder="Filter courses"
               v-model="filter"
               ref="filter">
    </div>

    <ul class="sidebar-list"
        v-if="sortedCourses.length > 0">
        <li class="sidebar-list-section-header text-muted"
            v-if="showTopCourses">
            <small>Courses with closest deadlines</small>
        </li>

        <course-list-item v-for="course in topCourses"
                          :key="`top-course-${course.id}`"
                          v-if="showTopCourses"
                          :course="course"
                          :current-id="currentCourse && currentCourse.id"
                          @open-menu="$emit('open-menu', $event)"/>

        <li v-if="showTopCourses">
            <hr class="separator">
        </li>

        <course-list-item v-for="course in (filteredCourses || sortedCourses)"
                          :key="`sorted-course-${course.id}`"
                          :course="course"
                          :current-id="currentCourse && currentCourse.id"
                          :extra-course-data="courseExtraDataToDisplay[course.id]"
                          @open-menu="$emit('open-menu', $event)"/>
    </ul>
    <span v-else class="sidebar-list no-items-text">
        You don't have any courses yet.
    </span>

    <hr class="separator"
        v-if="showAddButton">

    <b-button-group class="sidebar-footer">
        <b-btn class="add-course-button sidebar-footer-button"
               :id="addButtonId"
               v-if="showAddButton"
               v-b-popover.hover.top="'Add new course'">
            <icon name="plus" style="margin-right: 0;"/>
            <b-popover :target="addButtonId"
                       :id="popoverId"
                       triggers="click"
                       placement="top"
                       custom-class="no-max-width">
                <submit-input style="width: 18rem;"
                              placeholder="New course name"
                              @create="createNewCourse"
                              @cancel="closePopover"/>
            </b-popover>
        </b-btn>
    </b-button-group>
</div>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';

import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/plus';

import { cmpNoCase } from '@/utils';
import { Counter } from '@/utils/counter';

import SubmitInput from '../SubmitInput';
import CourseListItem from './CourseListItem';

let idNum = 0;

export default {
    name: 'course-list',

    props: {
        data: {
            type: Object,
            default: null,
        },
    },

    data() {
        const id = idNum++;
        return {
            filter: '',
            addButtonId: `course-add-btn-${id}`,
            popoverId: `course-add-popover-${id}`,
            showAddButton: false,
        };
    },

    computed: {
        ...mapGetters('courses', ['courses']),

        topCourses() {
            const now = this.$root.$now;

            function closestDeadline(course) {
                if (!course.assignments.length) {
                    return Infinity;
                }
                return Math.min(
                    ...course.assignments.map(assig => {
                        if (assig.hasDeadline) {
                            return Math.abs(assig.deadline.diff(now));
                        } else {
                            return Infinity;
                        }
                    }),
                );
            }

            const lookup = Object.values(this.courses).reduce((res, course) => {
                const deadline = closestDeadline(course);
                if (deadline !== Infinity) {
                    res[course.id] = deadline;
                }
                return res;
            }, {});

            return Object.values(this.courses)
                .filter(a => lookup[a.id] != null)
                .sort((a, b) => lookup[a.id] - lookup[b.id])
                .slice(0, 3);
        },

        showTopCourses() {
            return !this.filter && this.sortedCourses.length >= this.topCourses.length + 2;
        },

        sortedCourses() {
            return Object.values(this.courses).sort((a, b) => cmpNoCase(a.name, b.name));
        },

        filteredCourses() {
            if (!this.filter) {
                return null;
            }

            const filterParts = this.filter.toLocaleLowerCase().split(' ');

            return this.sortedCourses.filter(course =>
                filterParts.every(part => course.name.toLocaleLowerCase().indexOf(part) > -1),
            );
        },

        currentCourse() {
            return this.courses[this.$route.params.courseId];
        },

        // TODO: This is duplicated from HomeGrid.vue. We should factor it out into a Course or
        // CourseCollection model or something.
        courseExtraDataToDisplay() {
            const courses = this.sortedCourses;

            const getNameAndYear = c => `${c.name} (${c.created_at.slice(0, 4)})`;

            const courseName = new Counter(courses.map(c => c.name));
            const courseNameAndYear = new Counter(courses.map(getNameAndYear));

            return courses.reduce((acc, course) => {
                if (courseName.getCount(course.name) > 1) {
                    if (courseNameAndYear.getCount(getNameAndYear(course)) > 1) {
                        acc[course.id] = course.created_at.slice(0, 10);
                    } else {
                        acc[course.id] = course.created_at.slice(0, 4);
                    }
                } else {
                    acc[course.id] = null;
                }
                return acc;
            }, {});
        },
    },

    async mounted() {
        this.$root.$on('sidebar::reload', this.reload);

        this.$hasPermission('can_create_courses').then(create => {
            this.showAddButton = create;
        });

        const res = this.loadCourses();
        if (res != null) {
            this.$emit('loading');
            await res;
            this.$emit('loaded');
        }

        await this.$nextTick();

        const activeEl = document.activeElement;
        if (
            !activeEl ||
            !activeEl.matches('input, textarea') ||
            activeEl.closest('.sidebar .submenu')
        ) {
            this.$refs.filter.focus();
        }
    },

    destroyed() {
        this.$root.$off('sidebar::reload', this.reload);
    },

    methods: {
        ...mapActions('courses', ['loadCourses', 'reloadCourses']),

        reload() {
            this.$emit('loading');
            this.reloadCourses().then(() => {
                this.$emit('loaded');
            });
        },

        createNewCourse(name, resolve, reject) {
            this.$http
                .post('/api/v1/courses/', {
                    name,
                })
                .then(
                    res => {
                        const course = res.data;
                        res.onAfterSuccess = () => {
                            this.$emit('loading');
                            this.reloadCourses().then(() => {
                                this.$emit('loaded');
                                this.$router.push({
                                    name: 'manage_course',
                                    params: {
                                        courseId: course.id,
                                    },
                                });
                            });
                        };

                        resolve(res);
                    },
                    err => {
                        reject(err);
                    },
                );
        },

        closePopover() {
            this.$root.$emit('bv::hide::popover', this.popoverId);
        },
    },

    components: {
        CourseListItem,
        Icon,
        SubmitInput,
    },
};
</script>
