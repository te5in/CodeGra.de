<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="grade-viewer"
     v-b-popover.top.hover="globalPopover"
     :class="globalPopover ? 'cursor-not-allowed' : undefined">
    <b-collapse id="rubric-collapse"
                v-if="showRubric"
                v-model="rubricOpen">
        <rubric-viewer :assignment="assignment"
                       :submission="submission"
                       :editable="realEditable"
                       :visible="rubricOpen"
                       @change="rubricGradeChanged"
                       @rubricUpdated="rubricResult = $event"
                       @outOfSyncUpdated="outOfSyncItems = $event.size"
                       ref="rubricViewer"
                       class="mb-3"/>
    </b-collapse>

    <b-form-fieldset class="mb-0">
        <b-input-group>
            <b-input-group-prepend>
                <submit-button ref="submitButton"
                               class="submit-grade-btn"
                               v-if="realEditable"
                               :submit="putGrade"
                               @success="gradeUpdated"/>
                <span class="input-group-text" v-else>Grade</span>
            </b-input-group-prepend>

            <input type="number"
                   class="form-control"
                   :disabled="!!globalPopover"
                   name="grade-input"
                   step="any"
                   min="0"
                   :max="maxAllowedGrade"
                   :readonly="!realEditable"
                   :placeholder="editable ? 'Grade' : 'Not yet available'"
                   @keydown.enter="$refs.submitButton.onClick"
                   @input="rubricOverridden = showRubric"
                   v-model="grade"/>

            <b-input-group-append class="text-right rubric-score d-inline text-center"
                                  :class="{ warning: rubricOverridden, 'help-cursor': rubricOverridden }"
                                  v-if="showRubric"
                                  is-text>
                <span v-b-popover.top.hover="rubricOverridden ? 'Rubric grade was overridden.' : ''">
                    {{ rubricScore }}
                </span>
            </b-input-group-append>

            <b-input-group-append class="delete-button-group"
                                  v-if="realEditable">
                <b-popover :triggers="showDeleteButton ? 'hover' : ''"
                           placement="top"
                           target="delete-grade-button">
                    {{ deleteButtonText }}
                </b-popover>
                <submit-button id="delete-grade-button"
                               class="delete-button"
                               variant="danger"
                               :disabled="!showDeleteButton"
                               :submit="deleteGrade"
                               @success="afterDeleteGrade"
                               :confirm="deleteConfirmText">
                    <icon :name="rubricOverridden ? 'reply' : 'times'"/>
                </submit-button>
            </b-input-group-append>

            <b-input-group-append v-if="showRubric">
                <b-button variant="secondary"
                          v-b-popover.top.hover="'Toggle rubric'"
                          v-b-toggle.rubric-collapse>
                    <loader :scale="1" v-if="rubricResult == null" />
                    <icon name="th" v-else/>
                </b-button>
            </b-input-group-append>

            <b-input-group-append class="text-right rubric-score warning help-cursor"
                                  v-if="isRubricChanged"
                                  is-text
                                  v-b-popover.hover.top="'Press the submit button to submit the changes.'">
                The rubric is not saved yet!
            </b-input-group-append>
        </b-input-group>
    </b-form-fieldset>
</div>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';

import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/th';
import 'vue-awesome/icons/info';
import 'vue-awesome/icons/refresh';
import 'vue-awesome/icons/reply';
import 'vue-awesome/icons/times';
import { formatGrade, isDecimalNumber } from '@/utils';
import RubricViewer from './RubricViewer';
import SubmitButton from './SubmitButton';
import Loader from './Loader';

export default {
    name: 'grade-viewer',

    props: {
        editable: {
            type: Boolean,
            default: false,
        },
        rubricStartOpen: {
            type: Boolean,
            default: false,
        },
        assignment: {
            type: Object,
            required: true,
        },
        submission: {
            type: Object,
            required: true,
        },

        notLatest: {
            type: Boolean,
            default: false,
        },

        groupOfUser: {
            type: Object,
            default: null,
        },
    },

    data() {
        return {
            grade: this.submission.grade,
            rubricOpen: this.rubricStartOpen && !this.notLatest,
            rubricOverridden: null,
            outOfSyncItems: 0,
            rubricResult: null,
        };
    },

    computed: {
        ...mapGetters('rubrics', {
            allRubricResults: 'results',
        }),

        globalPopover() {
            if (this.notLatest) {
                return `This is not the latest submission by ${this.$utils.nameOfUser(
                    this.submission.user,
                )} so you cannot edit the grade. This grade will not be passed back to your LMS`;
            } else if (this.groupOfUser) {
                return `This user is member of the group "${
                    this.groupOfUser.group.name
                }", which also created a submission. Therefore, this submission is not the latest of this user.`;
            } else {
                return '';
            }
        },

        realEditable() {
            return this.editable && !this.notLatest;
        },

        rubric() {
            return this.assignment.rubricModel;
        },

        rubricPoints() {
            return this.rubricResult && this.rubricResult.points;
        },

        rubricGrade() {
            if (this.rubric == null || this.rubricResult == null) {
                return null;
            }

            let grade;
            if (this.rubricResult.selected.length === 0) {
                grade = null;
            } else {
                grade = Math.max(0, this.rubricPoints / this.rubric.maxPoints * 10);
                grade = Math.min(grade, this.maxAllowedGrade || 10);
            }

            return formatGrade(grade);
        },

        isRubricChanged() {
            const incremental = UserConfig.features.incremental_rubric_submission;
            const show = this.showRubric;
            const outOfSync = this.outOfSyncItems;

            return !incremental && show && outOfSync > 0;
        },

        rubricHasSelectedItems() {
            return (this.rubricResult && this.rubricResult.points) != null;
        },

        maxAllowedGrade() {
            return (this.assignment && this.assignment.max_grade) || 10;
        },

        deleteButtonText() {
            if (this.showRubric) {
                if (this.rubricOverridden) {
                    return 'Reset the grade to the grade from the rubric';
                } else {
                    return 'Clear the rubric';
                }
            } else {
                return 'Delete grade';
            }
        },

        deleteConfirmText() {
            if (this.showRubric) {
                if (this.rubricOverridden) {
                    return 'Are you sure you want to reset the grade?';
                } else {
                    return 'Are you sure you want to clear the rubric?';
                }
            } else {
                return 'Are you sure you want to clear the grade?';
            }
        },

        showDeleteButton() {
            if (!this.realEditable) {
                return false;
            } else if (this.rubricOverridden) {
                return true;
            } else if (this.showRubric) {
                return this.rubricHasSelectedItems;
            } else {
                return this.grade != null;
            }
        },

        showRubric() {
            return !!(this.rubric && this.rubric.rows.length);
        },

        rubricScore() {
            const toFixed = val => {
                const fval = parseFloat(val);
                return fval
                    .toFixed(10)
                    .replace(/[.,]([0-9]*?)0*$/, '.$1')
                    .replace(/\.$/, '');
            };
            const points = this.rubricPoints;
            const scored = points ? toFixed(points) : 0;
            const max = toFixed(this.rubric.maxPoints);
            return `${scored} / ${max}`;
        },

        submissionGrade() {
            return this.submission.grade;
        },
    },

    watch: {
        assignment: {
            immediate: true,
            handler() {
                this.storeLoadRubric(this.assignment.id);
            },
        },

        submission: {
            immediate: true,
            handler() {
                const grade = this.submission.grade;
                if (grade) {
                    this.grade = formatGrade(grade);
                    this.rubricOverridden = this.submission.grade_overridden ? true : null;
                } else {
                    this.grade = null;
                }
                this.storeLoadRubricResult({
                    submissionId: this.submission.id,
                });
            },
        },

        submissionGrade: {
            immediate: false,
            handler(newGrade) {
                this.grade = formatGrade(newGrade);
            },
        },
    },

    async mounted() {
        this.$root.$on('open-rubric-category', () => {
            this.rubricOpen = true;
        });
    },

    destroyed() {
        this.$root.$off('open-rubric-category');
    },

    methods: {
        ...mapActions('submissions', {
            storeUpdateSubmission: 'updateSubmission',
        }),

        ...mapActions('courses', {
            storeLoadRubric: 'loadRubric',
        }),

        ...mapActions('rubrics', {
            storeLoadRubricResult: 'loadResult',
        }),

        gradeUpdated(overridden) {
            this.rubricOverridden = overridden;
            this.storeUpdateSubmission({
                assignmentId: this.assignment.id,
                submissionId: this.submission.id,
                submissionProps: {
                    grade: this.grade,
                    grade_overridden: overridden,
                },
            });
        },

        rubricGradeChanged(rubricResult) {
            this.rubricResult = rubricResult;
            this.grade = this.rubricGrade;
            this.rubricOverridden = false;
        },

        deleteGrade() {
            if (this.showRubric && !this.rubricOverridden) {
                return this.$refs.rubricViewer.clearSelected();
            } else if (this.isRubricChanged) {
                this.grade = this.rubricGrade;
                return null;
            } else {
                return this.$http.patch(`/api/v1/submissions/${this.submission.id}`, {
                    grade: null,
                });
            }
        },

        afterDeleteGrade(response) {
            const grade = response && response.data && response.data.grade;

            if (grade !== undefined) {
                this.grade = formatGrade(grade) || null;
            }

            this.gradeUpdated(false);
        },

        putGrade() {
            const grade = parseFloat(this.grade);

            if (grade != null && !isDecimalNumber(grade)) {
                throw new Error('Grade must be a number');
            }

            const overridden = this.rubricOverridden;
            const normalGrade = overridden || !this.showRubric;

            if (
                !(grade >= 0 && grade <= this.maxAllowedGrade) &&
                normalGrade &&
                !Number.isNaN(grade)
            ) {
                throw new Error(`Grade must be between 0 and ${this.maxAllowedGrade}.`);
            }

            let req = Promise.resolve();

            if (this.showRubric) {
                req = this.$refs.rubricViewer.submitAllItems().then(() => false);
            }

            if (!this.showRubric || overridden) {
                req = req.then(() => this.submitNormalGrade(grade)).then(() => overridden);
            }

            return req;
        },

        submitNormalGrade(grade) {
            return this.$http
                .patch(`/api/v1/submissions/${this.submission.id}`, { grade })
                .then(() => {
                    this.grade = formatGrade(grade);
                });
        },
    },

    components: {
        Icon,
        SubmitButton,
        RubricViewer,
        Loader,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.cursor-not-allowed {
    cursor: not-allowed !important;
}

input:read-only {
    color: black;
    background-color: white;
    .grade-viewer:not(.cursor-not-allowed) & {
        cursor: text;
    }
    pointer-events: all;
    user-select: initial;
}

.help-cursor {
    cursor: help;
}
</style>
