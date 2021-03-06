<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="home-grid">
    <local-header>
        <template slot="title">
            Welcome {{ nameOfUser }}!
        </template>

        <div class="search-logo-wrapper">
            <input class="search form-control mr-3"
                   :value="searchString"
                   v-debounce="newSearchString => { searchString = newSearchString }"
                   ref="searchInput"
                   placeholder="Type to search"/>
            <cg-logo :small="$root.$isSmallWindow" :inverted="!darkMode" />
        </div>
    </local-header>

    <b-alert show v-if="showReleaseNote" variant="info">
        A new version of CodeGrade has been released:
        <b>{{ UserConfig.release.version }}</b>.
        {{ UserConfig.release.message }} You can check the entire
        changelog <a href="https://docs.codegra.de/about/changelog.html"
                     target="_blank"
                     class="alert-link">here</a>.
    </b-alert>

    <loader v-if="loadingCourses" page-loader/>

    <template v-else-if="courses.length === 0">
        <h3 class="text-center font-italic text-muted">You have no courses yet!</h3>
    </template>

    <template v-else-if="filteredCourses.length === 0">
        <h3 class="text-center font-italic text-muted">No matching courses found!</h3>
    </template>

    <masonry :cols="{default: 3, [$root.largeWidth]: 2, [$root.mediumWidth]: 1 }"
             :gutter="30"
             class="outer-block outer-course-wrapper"
             v-else>
        <div class="course-wrapper"
             v-for="course, idx in filteredCourses"
             :key="course.id"
             v-if="idx < amountCoursesToShow">
            <b-card no-body>
                <b-card-header :class="`text-${getColorPair(course.name).color}`"
                               :style="{ backgroundColor: `${getColorPair(course.name).background} !important` }">
                    <div style="display: flex">
                        <div class="course-name">
                            <b>{{ course.name }}</b>
                            <i v-if="courseExtraDataToDisplay[course.id]">
                                ({{ courseExtraDataToDisplay[course.id] }})
                            </i>
                        </div>
                        <router-link v-if="course.canManage"
                                     :to="manageCourseRoute(course)"
                                     v-b-popover.window.top.hover="'Manage course'"
                                     class="course-manage">
                            <icon name="gear"/>
                        </router-link>
                    </div>
                </b-card-header>
                <b-card-body class="card-no-padding">
                    <div class="card-text">
                        <table class="table table-hover assig-list"
                               v-if="course.assignments.length > 0">
                            <tbody>
                                <router-link v-for="{ assignment, filtered } in getAssignments(course)"
                                             :key="assignment.id"
                                             :to="submissionsRoute(assignment)"
                                             :class="filtered ? 'text-muted' : ''"
                                             class="assig-list-item">
                                    <td>
                                        <span>{{ assignment.name }}</span><br>

                                        <small v-if="assignment.hasDeadline">
                                            Due <cg-relative-time :date="assignment.deadline" />
                                        </small>
                                        <small v-else class="text-muted font-italic">
                                            No deadline
                                        </small>
                                    </td>
                                    <td class="shrink">
                                        <assignment-state :assignment="assignment"
                                                          :editable="false"
                                                          size="sm"/>
                                    </td>
                                    <td v-if="assignment.canManage"
                                        class="shrink">
                                        <router-link :to="manageAssignmentRoute(assignment)"
                                                     v-b-popover.window.top.hover="'Manage assignment'">
                                            <icon name="gear" class="gear-icon"/>
                                        </router-link>
                                    </td>
                                </router-link>
                            </tbody>
                        </table>

                        <p class="m-3 font-italic text-muted" v-else>
                            No assignments for this course.
                        </p>
                    </div>
                </b-card-body>
            </b-card>
        </div>
    </masonry>


    <b-btn class="extra-load-btn"
           v-if="moreCoursesAvailable && !loadingCourses"
           @click="showMoreCourses()">
        <loader v-if="renderingMoreCourses > 0" :scale="1" class="py-1"/>
        <span v-else>
            Load more courses
        </span>
        <infinite-loading @infinite="showMoreCourses" :distance="150">
            <div slot="spinner"></div>
            <div slot="no-more"></div>
            <div slot="no-results"></div>
            <div slot="error" slot-scope="err">
                {{ err }}
            </div>
        </infinite-loading>
    </b-btn>
</div>
</template>


<script>
import moment from 'moment';
import { mapGetters, mapActions } from 'vuex';
import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/gear';
import InfiniteLoading from 'vue-infinite-loading';

import { hashString, cmpNoCaseMany } from '@/utils';
import { Counter } from '@/utils/counter';

import AssignmentState from './AssignmentState';
import UserInfo from './UserInfo';
import Loader from './Loader';
import LocalHeader from './LocalHeader';
import CgLogo from './CgLogo';

// We can't use the COLOR_PAIRS from constants.js because that one is slightly
// different and because we use hashes to index this list that would change most
// colors for everyone.
const COLOR_PAIRS = [
    { background: 'rgb(112, 163, 162)', color: 'dark' },
    { background: 'rgb(223, 211, 170)', color: 'dark' },
    { background: 'rgb(223, 184, 121)', color: 'dark' },
    { background: 'rgb(149, 111,  72)', color: 'light' },
    { background: 'rgb( 79,  95,  86)', color: 'light' },
    { background: 'rgb(167, 174, 145)', color: 'dark' },
    { background: 'rgb(215, 206, 166)', color: 'dark' },
    { background: 'rgb(204,  58,  40)', color: 'light' },
    { background: 'rgb( 89, 141, 134)', color: 'light' },
    { background: 'rgb(230, 220, 205)', color: 'dark' },
    { background: 'rgb(214, 206,  91)', color: 'dark' },
    { background: 'rgb(217, 126, 113)', color: 'dark' },
    { background: 'rgb( 93, 141, 125)', color: 'light' },
    { background: 'rgb(210, 207, 159)', color: 'dark' },
    { background: 'rgb(234, 219, 147)', color: 'dark' },
    { background: 'rgb(203,  84,  82)', color: 'light' },
    { background: 'rgb(101, 104, 108)', color: 'light' },
    { background: 'rgb(180, 174, 164)', color: 'dark' },
    { background: 'rgb(231, 238, 233)', color: 'dark' },
    { background: 'rgb(234, 182, 108)', color: 'dark' },
];

// The amount of extra courses that should be loaded when we reach the end of
// the infinite scroll list. This is a multiple of 3 and of 2 (and 1 ofc) as
// those are the amount of columns we use in our masonry. So by using a multiple
// we increase the chance that we fill the masonry nice and even.
const EXTRA_COURSES_AMOUNT = 12;

export default {
    name: 'home-grid',

    data() {
        return {
            loadingCourses: true,
            UserConfig,
            amountCoursesToShow: EXTRA_COURSES_AMOUNT,
            searchString: this.$route.query.filter || '',
            renderingMoreCourses: 0,
        };
    },

    computed: {
        ...mapGetters('courses', { unsortedCourses: 'courses' }),
        ...mapGetters('user', { nameOfUser: 'name' }),
        ...mapGetters('pref', ['darkMode']),

        courses() {
            return Object.values(this.unsortedCourses).sort((a, b) =>
                cmpNoCaseMany([b.created_at, a.created_at], [a.name, b.name]),
            );
        },

        // TODO: This is duplicated in Sidebar/CourseList.vue. We should factor
        // it out into a Course or CourseCollection model or something.
        courseExtraDataToDisplay() {
            const getNameAndYear = c => `${c.name} (${c.created_at.slice(0, 4)})`;

            const courseName = new Counter(this.courses.map(c => c.name));
            const courseNameAndYear = new Counter(this.courses.map(getNameAndYear));

            return this.courses.reduce((acc, course) => {
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

        filteredCourses() {
            if (!this.searchString) {
                return this.courses;
            }
            const filter = (this.searchString || '').toLowerCase().split(' ');
            return this.courses.filter(c =>
                filter.every(
                    sub =>
                        c.name.toLowerCase().indexOf(sub) >= 0 ||
                        c.assignments.some(a => a.name.toLowerCase().indexOf(sub) >= 0),
                ),
            );
        },

        showReleaseNote() {
            return (
                UserConfig.release.message &&
                this.$root.$now.diff(moment(UserConfig.release.date), 'days') < 7
            );
        },

        // Are there more courses available. If this is true we should show the
        // infinite loader.
        moreCoursesAvailable() {
            return this.filteredCourses.length > this.amountCoursesToShow;
        },
    },

    async mounted() {
        await Promise.all([this.$afterRerender(), this.loadCourses()]);
        this.loadingCourses = false;

        const searchInput = await this.$waitForRef('searchInput');
        if (searchInput != null) {
            searchInput.focus();
        }
    },

    watch: {
        searchString() {
            const newQuery = Object.assign({}, this.$route.query);
            newQuery.filter = this.searchString || undefined;

            this.$router.replace({
                query: newQuery,
                hash: this.$route.hash,
            });
        },
    },

    methods: {
        ...mapActions('courses', ['loadCourses']),

        getAssignments(course) {
            if (!this.searchString) {
                return course.assignments.map(a => ({ assignment: a, filtered: false }));
            }
            const filter = (this.searchString || '').toLowerCase().split(' ');
            if (filter.every(sub => course.name.toLowerCase().indexOf(sub) >= 0)) {
                return course.assignments.map(a => ({ assignment: a, filtered: false }));
            }

            // Make sure the assignments the user is searching for appear at the
            // top
            const filtered = [];
            const nonFiltered = [];
            course.assignments.forEach(a => {
                if (filter.some(sub => a.name.toLowerCase().indexOf(sub) >= 0)) {
                    nonFiltered.push({
                        assignment: a,
                        filtered: false,
                    });
                } else {
                    filtered.push({
                        assignment: a,
                        filtered: true,
                    });
                }
            });
            return [...nonFiltered, ...filtered];
        },

        getColorPair(name) {
            const hash = hashString(name);
            return COLOR_PAIRS[hash % COLOR_PAIRS.length];
        },

        manageCourseRoute(course) {
            return {
                name: 'manage_course',
                params: {
                    courseId: course.id,
                },
            };
        },

        manageAssignmentRoute(assignment) {
            return {
                name: 'manage_assignment',
                params: {
                    courseId: assignment.course.id,
                    assignmentId: assignment.id,
                },
            };
        },

        submissionsRoute(assignment) {
            return {
                name: 'assignment_submissions',
                params: {
                    courseId: assignment.course.id,
                    assignmentId: assignment.id,
                },
            };
        },

        // This method should be called when the infinite loader comes into view.
        // The optional $state parameter should be the state parameter of the
        // vue-infinite-loader plugin, and should have two callable props:
        // `loaded` and `complete`.
        async showMoreCourses($state = null) {
            this.renderingMoreCourses += 1;
            await this.$afterRerender();
            this.amountCoursesToShow += EXTRA_COURSES_AMOUNT;
            this.renderingMoreCourses -= 1;

            if ($state) {
                if (this.moreCoursesAvailable) {
                    $state.loaded();
                } else {
                    this.renderingMoreCourses = 0;
                    $state.complete();
                }
            }
        },
    },

    components: {
        AssignmentState,
        CgLogo,
        Icon,
        UserInfo,
        Loader,
        LocalHeader,
        InfiniteLoading,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.home-grid {
    display: flex;
    flex-direction: column;
    min-height: 100%;
}

.cg-logo {
    height: 1.5rem;
}

.home-grid .outer-block {
    .card-body.card-no-padding {
        padding: 0;
    }

    .assig-list {
        margin-bottom: 0;

        .assig-list-item {
            display: table-row;

            @{dark-mode},
            @{dark-mode} .fa-icon {
                color: rgb(210, 212, 213);
            }

            &:first-child td {
                border-top-width: 0;
            }

            &:nth-of-type(even) {
                background-color: rgba(0, 0, 0, 0.05);
            }

            &:hover {
                background-color: rgba(0, 0, 0, 0.075);
            }
        }

        a:hover {
            text-decoration: none;

            .fa-icon {
                border-bottom-color: transparent;
            }
        }

        .fa-icon {
            margin-top: 5px;
        }
    }

    .course-wrapper {
        padding-bottom: 1em;

        .card {
            // Dont render content over the border
            overflow: hidden;
        }

        .card-body {
            @media @media-medium {
                max-height: 15em;
                overflow: auto;
            }
        }

        .card-header {
            padding: 0.75rem;

            .course-name {
                flex: 1 1 auto;
            }

            .course-manage {
                display: flex;
                flex: 0 0 auto;
            }

            .fa-icon {
                display: block;
                margin: auto;
            }
        }

        .card-header.text-dark {
            color: @text-color !important;

            .fa-icon {
                fill: @text-color;
            }
        }

        .card-header.text-light {
            color: @color-lighter-gray !important;

            .fa-icon {
                fill: @text-color-dark;
            }
        }
    }
}

a {
    @{dark-mode} {
        color: @text-color-dark;

        &:hover {
            color: darken(@text-color-dark, 10%);
        }
    }

    .gear-icon {
        border-bottom: 1px solid transparent;
    }

    &:hover .gear-icon {
        border-bottom: 1px solid lighten(@color-primary, 10%);

        @{dark-mode} {
            border-color: darken(@text-color-dark, 10%);
        }
    }
}

.search {
    flex: 1 1 auto;
}

.search-logo-wrapper {
    flex: 0 0 auto;
    display: flex;
    align-items: center;
}

.extra-load-btn {
    margin: 0 auto;
}
</style>
