<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="grade-viewer">
    <b-collapse id="rubric-collapse"
                v-model="rubricOpen"
                v-if="showRubric">
        <rubric-viewer
            v-model="rubricPoints"
            style="margin-bottom: 15px;"
            :editable="editable"
            :assignment="assignment"
            :submission="submission"
            :rubric="rubric"
            ref="rubricViewer"/>
    </b-collapse>

    <b-form-fieldset class="grade-fieldset">
        <b-input-group>
            <b-input-group-prepend>
                <submit-button ref="submitButton"
                               v-if="editable"
                               :submit="putGrade"
                               @success="gradeUpdated"/>
                <span class="input-group-text" v-else>Grade</span>
            </b-input-group-prepend>

            <input type="number"
                   class="form-control"
                   step="any"
                   min="0"
                   :max="maxAllowedGrade"
                   :readonly="!editable"
                   placeholder="Grade"
                   @keydown.enter="$refs.submitButton.onClick"
                   v-model="grade"/>

            <b-input-group-append class="text-right rubric-score"
                                  :class="{'grade-warning': rubricOverridden}"
                                  style="text-align: center !important; display: inline;"
                                  v-if="showRubric"
                                  is-text>
                <span v-if="rubricOverridden"
                      v-b-popover.top.hover="'Rubric grade was overridden.'">
                    {{ rubricScore }}
                </span>
                <span v-else>{{ rubricScore }}</span>
            </b-input-group-append>

            <b-input-group-append class="delete-button-group"
                                  v-if="editable">
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
                               @success="afterDeleteGrade">
                    <icon :name="rubricOverridden ? 'reply' : 'times'"/>
                </submit-button>
            </b-input-group-append>

            <b-input-group-append v-if="showRubric">
                <b-button variant="secondary"
                          v-b-popover.top.hover="'Toggle rubric'"
                          v-b-toggle.rubric-collapse>
                    <icon name="th"/>
                </b-button>
            </b-input-group-append>

            <b-input-group-append class="text-right rubric-score grade-warning"
                                  v-if="isRubricChanged()"
                                  is-text
                                  v-b-popover.hover.top="'Press the submit button to submit the changes.'">
                The rubric is not saved yet!
            </b-input-group-append>
        </b-input-group>
    </b-form-fieldset>
</div>
</template>

<script>
import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/th';
import 'vue-awesome/icons/info';
import 'vue-awesome/icons/refresh';
import 'vue-awesome/icons/reply';
import 'vue-awesome/icons/times';
import { mapActions, mapGetters } from 'vuex';
import { formatGrade, isDecimalNumber } from '@/utils';
import RubricViewer from './RubricViewer';
import SubmitButton from './SubmitButton';

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
            default: {},
        },
        submission: {
            type: Object,
            default: null,
        },
        rubric: {
            type: Object,
            default: {},
        },
    },

    data() {
        return {
            grade: this.submission.grade,
            rubricPoints: {},
            rubricHasSelectedItems: false,
            rubricOpen: this.rubricStartOpen,
        };
    },

    computed: {
        maxAllowedGrade() {
            return this.assignment.max_grade == null ? 10 : this.assignment.max_grade;
        },

        deleteButtonText() {
            if (this.showRubric) {
                if (this.rubricOverridden) {
                    return 'Reset the grade to the grade from the rubric';
                }
                return 'Clear the rubric';
            }
            return 'Delete grade';
        },

        showDeleteButton() {
            if (!this.editable) {
                return false;
            }
            if (this.showRubric) {
                return this.rubricHasSelectedItems || this.rubricOverridden;
            }
            return this.grade != null;
        },

        showRubric() {
            return !!(this.rubric && this.rubric.rubrics.length);
        },

        rubricOverridden() {
            if (!this.showRubric || this.grade == null) {
                return false;
            }
            if (!this.rubricHasSelectedItems) {
                return true;
            }
            return this.grade !== formatGrade(this.$refs.rubricViewer.grade);
        },

        rubricScore() {
            const toFixed = val => {
                const fval = parseFloat(val);
                return fval
                    .toFixed(10)
                    .replace(/[.,]([0-9]*?)0*$/, '.$1')
                    .replace(/\.$/, '');
            };
            const scored = toFixed(this.rubricPoints.selected);
            const max = toFixed(this.rubricPoints.max);
            return `${scored} / ${max}`;
        },
    },

    watch: {
        submission() {
            this.grade = formatGrade(this.submission.grade) || 0;
        },

        rubric() {
            if (this.showRubric) {
                this.rubric.points.grade = this.grade;
            }
        },

        rubricPoints({ selected, max, grade }) {
            this.grade = formatGrade(grade) || null;
            this.rubricHasSelectedItems = this.$refs.rubricViewer.hasSelectedItems;
            this.rubricSelected = selected;
            this.rubricTotal = max;
            if (UserConfig.features.incremental_rubric_submission) {
                this.gradeUpdated();
            }
        },
    },

    async mounted() {
        if (this.showRubric) {
            this.rubric.points.grade = this.grade;
        }
    },

    methods: {
        gradeUpdated() {
            this.$emit('gradeUpdated', this.grade);
        },

        deleteGrade() {
            if (this.showRubric && !this.rubricOverridden) {
                return this.$refs.rubricViewer.clearSelected();
            } else if (this.isRubricChanged()) {
                // The object passed must be structured like this...
                this.grade = formatGrade(this.rubricPoints.grade);
                return Promise.resolve({ data: {} });
            } else {
                return this.$http.patch(`/api/v1/submissions/${this.submission.id}`, {
                    grade: null,
                });
            }
        },

        afterDeleteGrade(response) {
            if (response.data.grade !== undefined) {
                this.grade = formatGrade(response.data.grade) || null;
                this.gradeUpdated();
            }
        },

        putGrade() {
            if (!isDecimalNumber(this.grade)) {
                throw new Error('Grade must be a number');
            }

            const grade = parseFloat(this.grade);
            const normalGrade = this.rubricOverridden || !this.showRubric;

            if (
                !(grade >= 0 && grade <= this.maxAllowedGrade) &&
                normalGrade &&
                !Number.isNaN(grade)
            ) {
                throw new Error(`Grade must be between 0 and ${this.maxAllowedGrade}.`);
            }

            let req = Promise.resolve();

            if (this.showRubric) {
                req = this.$refs.rubricViewer.submitAllItems();
            }

            if (!this.showRubric || this.rubricOverridden) {
                req = req.then(() => this.submitNormalGrade(grade));
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

        ...mapActions({
            refreshSnippets: 'user/refreshSnippets',
        }),

        ...mapGetters({
            snippets: 'user/snippets',
        }),

        isRubricChanged() {
            return (
                this.showRubric &&
                this.$refs.rubricViewer &&
                !UserConfig.features.incremental_rubric_submission &&
                this.$refs.rubricViewer.outOfSync.size > 0
            );
        },
    },

    components: {
        Icon,
        SubmitButton,
        RubricViewer,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

input {
    &:read-only {
        &:focus {
            box-shadow: none !important;
        }
        color: black;
        background-color: white;
        cursor: text;
        pointer-events: all;
        user-select: initial;
    }
}

.grade-warning .input-group-text {
    background: fade(#f0ad4e, 50%) !important;
    cursor: help;

    #app.dark & {
        color: @text-color;
    }
}

.out-of-sync-alert {
    max-height: 3.2em;
    overflow-x: hidden;

    transition-property: all;
    transition-duration: 0.5s;
    margin-bottom: 1rem;
    transition-timing-function: cubic-bezier(0, 1, 0.5, 1);

    &.closed {
        max-height: 0;
        border-color: transparent;
        background: none;
        padding-top: 0;
        padding-bottom: 0;
        margin-bottom: 0;
    }
}

.grade-fieldset {
    margin-bottom: 0;
}
</style>

<style lang="less">
.grade-viewer .grade-submit .loader {
    height: 1.25rem;
}
</style>
