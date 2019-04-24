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
            <b-dropdown :text="internalValue.rubricCategory.header || 'Select a rubric category'"
                        class="category-dropdown">
                <b-dropdown-item v-for="cat in assignment.rubric"
                                 :key="cat.id"
                                 :disabled="!!disabledCategories[cat.id]"
                                 @click="$set(internalValue, 'rubricCategory', cat)">
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
                                    @delete="removeItem(index)"
                                    :step-types="stepTypes"
                                    editable/>
                </div>
            </SlickItem>
        </SlickList>

        <b-button-toolbar class="add-step-btns-wrapper">
            <b-btn v-for="stepType in stepTypes"
                   :key="stepType.value"
                   @click="addStep(stepType)"
                   class="add-step-btn text-muted"
                   v-b-popover.top.hover="`Add a new ${stepType.name} step`"
                   :style="{ 'background-color': stepType.color }"
                   variant="primary">
                <icon name="plus" /> {{ titleCase(stepType.name) }}
            </b-btn>
        </b-button-toolbar>

        <template slot="modal-footer">
            <b-button-toolbar justify style="width: 100%;">
                <submit-button variant="danger"
                               confirm="Are you sure you want to delete this suite?"
                               :submit="() => $emit('delete')"
                               label="Delete"/>
                <submit-button
                    variant="outline-danger"
                    :disabled="value.isEmpty()"
                    label="Cancel"
                    :submit="cancelEdit"/>
                <submit-button :submit="saveSuite"
                               :wait-at-least="0"
                               label="Save">
                    <div slot="error" v-if="!caseErrors.isEmpty()"
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
            <span>{{ value.rubricCategory.header }}</span>

            <div class="pencil"
                 @click="editSuite">
                <icon name="pencil"/>
            </div>
        </div>

        <div class="steps-wrapper">
            <ul class="steps-list">
                <li>
                    <table class="table" >
                        <thead>
                            <tr>
                                <th>No</th>
                                <th>Summary</th>
                                <th>Weight</th>
                            </tr>
                        </thead>
                        <auto-test-step :value="testStep"
                                        v-for="testStep, i in value.steps"
                                        :key="i"
                                        :index="i + 1"
                                        :step-types="stepTypes"/>
                    </table>
                </li>
            </ul>
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

import { deepCopy, titleCase, getUniqueId, withOrdinalSuffix } from '@/utils';

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

        editing: {
            type: Boolean,
            default: false,
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
            caseErrors: {
                steps: [],
                general: [],
                reset() {
                    this.steps = [];
                    this.general = [];
                },
                isEmpty() {
                    return this.steps.length === 0 && this.general.length === 0;
                },
            },
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
            return this.otherSuites.reduce(
                (res, other) => {
                    res[other.rubricCategory.id] = other;
                    return res;
                },
                {},
            );
        },

        stepTypes() {
            const isEmpty = val => !val.match(/[a-zA-Z0-9]/);
            const base = {
                metaTest: false,
                checkName: true,
                checkProgram: true,
                checkWeight: true,

                create() {
                    return {
                        name: '',
                        id: getUniqueId(),
                        type: this.value,
                        weight: 1,
                        program: '',
                        opened: true,
                    };
                },

                checkValid(step) {
                    const errs = [];

                    if (this.checkName && isEmpty(step.name)) {
                        errs.push('The name may not be empty.');
                    }
                    if (this.checkProgram && isEmpty(step.program)) {
                        errs.push('The program may not be empty.');
                    }
                    if (this.checkWeight && Number(step.weight) <= 0) {
                        errs.push('The weight should be a number higher than 0.');
                    }

                    return errs;
                },
            };
            const make = props => Object.create(base, Object.entries(props).reduce(
                (res, [key, value]) => {
                    res[key] = { value };
                    return res;
                },
                {},
            ));

            return [make({
                name: 'IO test',
                value: 'io_test',
                color: '#E7EEE9',
                metaTest: false,
                checkWeight: false,
                create() {
                    return {
                        ...base.create.call(this),
                        inputs: [this.createInput()],
                    };
                },
                createInput() {
                    return {
                        name: '',
                        id: getUniqueId(),
                        args: '',
                        stdin: '',
                        output: '',
                        options: [],
                        weight: 1,
                    };
                },
                checkValid(step) {
                    const errs = base.checkValid.call(this, step);

                    if (step.inputs.length === 0) {
                        errs.push('There should be at least one input output case.');
                    } else {
                        step.inputs.forEach((input, i) => {
                            const name = `${withOrdinalSuffix(i + 1)} input output case`;
                            if (isEmpty(input.name)) {
                                errs.push(`The name of the ${name} is emtpy.`);
                            }
                            if (Number(input.weight) <= 0) {
                                errs.push(`The weight of the ${name} should be a number higher than 0.`);
                            }
                        });
                    }

                    return errs;
                },
            }), make({
                name: 'run program',
                color: '#E6DCCD',
                value: 'run_program',
            }), make({
                name: 'custom output',
                color: '#DFD3AA',
                value: 'custom_output',
                create() {
                    return {
                        ...base.create.call(this),
                        regex: '(\\d+\\.?\\d*|\\.\\d+)',
                    };
                },
            }), make({
                name: 'check points',
                value: 'check_points',
                color: '#D6CE5B',
                metaTest: true,
                checkProgram: false,
                checkWeight: false,
                checkName: false,

                create() {
                    return {
                        ...base.create.call(this),
                        minPoints: 0,
                    };
                },

                checkValid(step, otherSteps) {
                    const errs = base.checkValid.call(this, step);
                    let weightBefore = 0;
                    for (let i = 0; i < otherSteps.length > 0; ++i) {
                        if (otherSteps[i].id === step.id) {
                            break;
                        }
                        weightBefore += Number(otherSteps[i].weight);
                    }
                    if (step.minPoints <= 0 || step.minPoints > weightBefore) {
                        errs.push(`The minimal amount of points should be achievable (which is ${weightBefore}) and higher than 0.`);
                    }

                    return errs;
                },
            })];
        },
    },

    methods: {
        noop() {
        },

        findStepType(step) {
            return this.stepTypes.find(v => v.value === step.type);
        },

        async editSuite() {
            this.internalValue = deepCopy(this.value);
            this.internalValue.steps.forEach(val => {
                val.opened = false;
            });
            this.showModal = true;
        },

        addStep(type) {
            this.internalValue.steps.push(type.create());
            this.internalValue.steps = this.internalValue.steps;
        },

        removeItem(index) {
            this.internalValue.steps.splice(index, 1);
        },

        ensureIsValid(value) {
            this.caseErrors.reset();

            if (value.steps.length === 0) {
                this.caseErrors.general.push('You should have at least one step.');
            }

            const stepErrors = value.steps.map(
                s => [s, this.findStepType(s).checkValid(s, value.steps)],
            );
            if (stepErrors.some(([, v]) => v.length > 0)) {
                this.caseErrors.steps = stepErrors;
            }

            if (!value.rubricCategory.id) {
                this.caseErrors.general.push('You should select a rubric category for this test suite.');
            }

            if (!this.caseErrors.isEmpty()) {
                throw new Error('The value is not valid.');
            }
        },

        saveSuite() {
            this.ensureIsValid(this.internalValue);

            const val = deepCopy(this.internalValue);
            this.$emit('input', val);

            this.$nextTick(() => {
                this.$refs.editModal.hide();
            });
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

.steps-wrapper {
    padding: 1.25rem;
    .steps-list {
        list-style: none;
        padding: 0;
        margin: 0;
    }
}

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
