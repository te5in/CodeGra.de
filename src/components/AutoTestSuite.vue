<template>
<div class="auto-test-suite"
     :class="value.isEmpty() ? 'empty-auto-test-suite' : ''">
    <b-modal class="edit-suite-modal"
             :style="{ cursor: slickItemMoving ? 'grabbing' : undefined }"
             ref="editModal"
             no-close-on-backdrop
             no-close-on-esc
             hide-header-close
             hide-header
             v-model="showModal"
             v-if="internalValue">
        <b-input-group prepend="Rubric category">
            <b-dropdown :text="internalValue.rubricRow.header || 'Select a rubric category'"
                        class="category-dropdown">
                <b-dropdown-item v-for="cat in assignment.rubric"
                                 :key="cat.id"
                                 :disabled="!!disabledCategories[cat.id]"
                                 @click="$set(internalValue, 'rubricRow', cat)">
                    <div v-b-popover.top.hover="disabledCategories[cat.id] ? 'This category is already used by another suite.' : ''"
                         class="category-wrapper">
                        <h5>{{ cat.header }}</h5>
                        <span class="rubric-description">
                            {{ cat.description }}
                        </span>
                    </div>
                </b-dropdown-item>
        </b-dropdown>
        </b-input-group>

        <hr/>

        <h5 style="text-align: center;">Steps</h5>
        <p v-if="internalValue.steps.length === 0" class="help-text">
            This suite contains no steps. Please add some using the buttons
            below.
        </p>
        <SlickList lock-axis="y"
                   lock-to-container-edges
                   @sort-start="slickItemMoving = true"
                   @sort-end="slickItemMoving = false"
                   use-drag-handle
                   v-model="internalValue.steps"
                   append-to=".edit-suite-modal">
            <SlickItem v-for="item, index in internalValue.steps"
                       :index="index"
                       :key="item.id"
                       class="auto-test-suite slick-item"
                       :class="slickItemMoving ? 'no-text-select' : ''">
                <div class="auto-test-suite-step item-wrapper">
                    <span v-handle class="handle">
                        <icon name="bars"/>
                    </span>
                    <auto-test-step v-model="internalValue.steps[index]"
                                    :index="index + 1"
                                    :test-types="stepTypes"
                                    @delete="internalValue.removeItem(index)"
                                    editable/>
                </div>
            </SlickItem>
        </SlickList>

        <b-button-toolbar class="add-step-btns-wrapper">
            <b-btn v-for="stepType in stepTypes"
                   :key="stepType.value"
                   @click="internalValue.addStep(createTestStep(stepType.name))"
                   class="add-step-btn text-muted"
                   v-b-popover.top.hover="`Add a new ${stepType.name} step`"
                   :style="{ 'background-color': stepType.color }"
                   variant="primary">
                <icon name="plus" /> {{ titleCase(stepType.name.replace(/_/g, ' ')) }}
            </b-btn>
        </b-button-toolbar>

        <template slot="modal-footer">
            <b-button-toolbar justify style="width: 100%;">
                <submit-button variant="danger"
                               confirm="Are you sure you want to delete this suite?"
                               :submit="() => internalValue.delete()"
                               @after-success="$emit('delete')"
                               label="Delete"/>
                <submit-button
                    variant="outline-danger"
                    :disabled="value.isEmpty()"
                    label="Cancel"
                    :submit="cancelEdit"/>
                <submit-button :submit="saveSuite"
                               label="Save">
                    <div slot="error" v-if="caseErrors != null"
                         class="custom-error-popover">
                        <template v-for="err in caseErrors.general">
                            {{ err }}
                        </template>
                        <template v-if="caseErrors.steps.length > 0">
                            Some steps are not valid:
                            <ul>
                                <li v-for="[step, errs], i in caseErrors.steps"
                                    :key="step.id"
                                    v-if="errs.length > 0">
                                    {{ withOrdinalSuffix(i + 1) }} step<span v-if="step.name">
                                        with name "{{ step.name }}"</span>:
                                    <ul>
                                        <li v-for="err in errs"
                                            :key="err">
                                            {{ err }}
                                        </li>
                                    </ul>
                                </li>
                            </ul>
                        </template>
                    </div>
                </submit-button>
            </b-button-toolbar>
        </template>
    </b-modal>

    <b-card no-body v-if="!value.isEmpty()">
        <div slot="header" class="title title-display">
            <span>{{ value.rubricRow.header }}</span>

            <div v-if="editable"
                 class="pencil"
                 @click="editSuite">
                <icon name="pencil"/>
            </div>

            <div v-else>
                {{ (100 * achievedPoints / pointsPossible).toFixed(2) }} %
            </div>
        </div>

        <div class="suite-steps">
            <table class="table steps-table">
                <thead>
                    <tr>
                        <th v-if="result"></th>
                        <th>No</th>
                        <th>Summary</th>
                        <th>Weight</th>
                        <th v-if="result">Pass</th>
                    </tr>
                </thead>
                <auto-test-step :value="testStep"
                                v-for="testStep, i in value.steps"
                                :test-types="stepTypes"
                                :key="i"
                                :index="i + 1"
                                :result="result"/>
            </table>
        </div>
    </b-card>
</div>
</template>

<script>
import { SlickList, SlickItem, HandleDirective } from 'vue-slicksort';

import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/bars';
import 'vue-awesome/icons/times';
import 'vue-awesome/icons/check';
import 'vue-awesome/icons/pencil';

import { titleCase, getUniqueId, withOrdinalSuffix } from '@/utils';

import SubmitButton from './SubmitButton';
import AutoTestStep from './AutoTestStep';

export default {
    name: 'auto-test-suite',

    props: {
        value: {
            type: Object,
            required: true,
        },

        assignment: {
            type: Object,
            required: true,
        },

        otherSuites: {
            type: Array,
            required: true,
        },

        editable: {
            type: Boolean,
            default: false,
        },

        editing: {
            type: Boolean,
            default: false,
        },

        result: {
            type: Object,
            default: null,
        },
    },

    data() {
        return {
            editingSet: false,
            newName: '',
            showModal: false,
            internalValue: null,
            slickItemMoving: false,
            titleCase,
            caseErrors: null,
            withOrdinalSuffix,
        };
    },

    watch: {
        editing: {
            handler() {
                if (this.editing) {
                    this.editSuite();
                }
            },
            immediate: true,
        },
    },

    computed: {
        disabledCategories() {
            return this.otherSuites.reduce((res, other) => {
                res[other.rubricRow.id] = other;
                return res;
            }, {});
        },

        stepTypes() {
            return [
                { name: 'io_test', color: '#E7EEE9' },
                { name: 'run_program', color: '#E6DCCD' },
                { name: 'custom_output', color: '#DFD3AA' },
                { name: 'check_points', color: '#D6CE5B' },
            ];
        },

        pointsPossible() {
            return this.value.steps.reduce((acc, step) => acc + (step.weight || 0), 0);
        },

        achievedPoints() {
            if (!this.result) {
                return 0;
            }

            const stepResults = this.result.stepResults;
            return this.value.steps
                .map(step => (stepResults[step.id].state === 'passed' ? step.weight : 0))
                .reduce((x, y) => x + y, 0);
        },
    },

    methods: {
        noop() {},

        createTestStep(type) {
            const res = {
                name: '',
                type,
                weight: 1,
                program: '',
                opened: true,
                hidden: false,
                data: {},
            };

            switch (type) {
                case 'io_test':
                    res.data.inputs = [
                        {
                            name: '',
                            id: getUniqueId(),
                            args: '',
                            stdin: '',
                            output: '',
                            options: [],
                            weight: 1,
                        },
                    ];
                    break;
                case 'custom_output':
                    res.data.regex = '(\\d+\\.?\\d*|\\.\\d+)';
                    break;
                case 'check_points':
                    res.data.min_points = 0;
                    break;
                case 'run_program':
                    res.data.program = '';
                    break;
                default:
                    throw new Error('Unknown test type!');
            }

            return res;
        },

        async editSuite() {
            this.internalValue = this.value.copy();
            this.internalValue.steps.forEach(val => {
                val.opened = false;
            });
            this.showModal = true;
        },

        saveSuite() {
            this.caseErrors = this.internalValue.getErrors();
            if (this.caseErrors) {
                throw new Error('The suite is not valid');
            } else {
                return this.internalValue.save().then(() => {
                    this.$refs.editModal.hide();
                    this.$emit('input', this.internalValue);
                    this.internalValue = null;
                });
            }
        },

        cancelEdit() {
            const modal = this.$refs.editModal;
            if (modal) {
                modal.hide();
                this.$emit('save-canceled');
            }
        },
    },

    components: {
        Icon,
        SubmitButton,
        SlickItem,
        SlickList,
        AutoTestStep,
    },

    directives: {
        handle: HandleDirective,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.title-display {
    display: flex;
    justify-content: space-between;
    vertical-align: center;

    .pencil {
        cursor: pointer;
    }
}

.handle {
    display: block;
    color: @text-color-muted;
    margin-right: 20px;
    cursor: grab;
    &.disabled-handle {
        cursor: not-allowed;
        color: @text-color-dark;
    }
}

.auto-test-step {
    flex: 1 1 auto;
}

.add-step-btns-wrapper {
    justify-content: center;

    .add-step-btn {
        border-color: rgba(0, 0, 0, 0.125) !important;
        box-shadow: none !important;
        &:not(:first-child) {
            margin-left: 1rem;
        }
        &:hover {
            filter: brightness(95%);
        }
    }
}

.custom-error-popover {
    text-align: left;
    ul {
        padding-left: 1rem;
        margin-bottom: 0;
    }
}

.dropdown-item {
    padding: 0;
    .category-wrapper {
        .rubric-description,
        h5 {
            padding: 0.25rem 1.5rem;
            margin: 0;
        }

        .rubric-description {
            white-space: initial;
            max-height: 5rem;
            display: block;
            overflow-y: auto;
        }
    }

    &:not(:last-child) {
        border-bottom: 1px solid rgba(0, 0, 0, 0.125);
    }

    &.disabled {
        cursor: not-allowed;
        opacity: 0.4;
        color: @color-primary !important;
    }
}

.suite-steps {
    max-height: 20rem;
    overflow: auto;
}

.steps-table {
    margin-bottom: 0;
}
</style>

<style lang="less">
.auto-test-suite .edit-suite-modal .modal-dialog {
    max-width: 891px;
}

.auto-test-suite .category-dropdown {
    flex: 1 1 auto;
    .dropdown-toggle {
        flex: 1 1 auto;
        border-top-left-radius: 0;
        border-bottom-left-radius: 0;
    }
    .dropdown-menu.show {
        overflow-y: auto;
        padding: 0;
    }
}

.auto-test-suite.slick-item {
    z-index: 99999;
    &.no-text-select {
        user-select: none;
        cursor: grabbing !important;
    }

    .auto-test-suite-step.item-wrapper {
        display: flex;
        align-items: center;
        padding-bottom: 1rem;
    }
}
</style>
