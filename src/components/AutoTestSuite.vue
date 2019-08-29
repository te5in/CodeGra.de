<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="auto-test-suite"
     :class="value.isEmpty() ? 'empty' : ''">
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
                                 @click="setRubricRow(cat)"
                                 :active="internalValue.rubricRow.id === cat.id"
                                 class="px-3 py-1">
                    <div v-b-popover.top.hover="disabledCategories[cat.id] ? 'This rubric category is already in use.' : ''">
                        <h5 class="mb-1">{{ cat.header }}</h5>
                        <span class="rubric-description">{{ cat.description }}</span>
                    </div>
                </b-dropdown-item>
            </b-dropdown>
        </b-input-group>

        <hr/>

        <h5 class="text-center mb-3">
            <icon class="expand-all-btn float-left text-muted"
                  :name="this.expandedSteps.length ? 'minus-square' : 'plus-square'"
                  @click.native="toggleAllSteps"
                  v-b-popover.hover.top="`${this.expandedSteps.length ? 'Collapse' : 'Expand'} all steps.`" />

            Steps
        </h5>

        <p v-if="internalValue.steps.length === 0" class="text-muted font-italic py-2">
            This category contains no steps. Please add some using the buttons below.
        </p>

        <SlickList lock-axis="y"
                   lock-to-container-edges
                   @sort-start="slickItemMoving = true"
                   @sort-end="slickItemMoving = false"
                   use-drag-handle
                   v-model="internalValue.steps"
                   append-to=".edit-suite-modal">
            <transition-group name="step">
                <SlickItem v-for="step, i in internalValue.steps"
                           :index="i"
                           :key="step.trackingId"
                           class="slick-item d-flex pb-3"
                           :class="slickItemMoving ? 'no-text-select' : ''" >
                    <div v-handle class="drag-handle d-flex align-self-stretch pr-3 text-muted">
                        <icon class="align-self-center" name="bars"/>
                    </div>

                    <auto-test-step v-model="internalValue.steps[i]"
                                    class="w-100"
                                    :index="i + 1"
                                    :test-types="stepTypes"
                                    :assignment="assignment"
                                    :is-continuous="isContinuous"
                                    @delete="internalValue.removeItem(i)"
                                    editable/>
                </SlickItem>
            </transition-group>
        </SlickList>

        <b-button-toolbar class="justify-content-center">
            <b-btn v-for="stepType in stepTypes"
                   :key="stepType.name"
                   @click="createTestStep(stepType.name)"
                   class="add-step-btn ml-2"
                   :style="{ 'background-color': stepType.color }"
                   v-b-popover.top.hover="stepType.help">
                <icon name="plus" /> {{ stepType.title }}
            </b-btn>
        </b-button-toolbar>

        <collapse v-model="advancedOptionsCollapsed" class="border rounded px-3 py-2 mt-3">
            <div slot="handle" class="collapse-handle mb-0 text-muted font-italic">
                <icon name="caret-down" />
                Advanced options
            </div>

            <div class="mt-3">
                <b-form-fieldset>
                    <label :for="timeoutId">
                        Timeout per step (seconds)

                        <description-popover hug-text>
                            <template slot="description">
                                If a single step takes longer than specified, the step will fail.
                            </template>
                        </description-popover>
                    </label>

                    <input :id="timeoutId"
                           class="form-control"
                           type="number"
                           min="0"
                           step="30"
                           v-model="internalValue.commandTimeLimit" />
                </b-form-fieldset>

                <b-form-fieldset class="mb-0">
                    <b-form-checkbox name="network-disabled"
                                     class="mr-1"
                                     v-model="internalValue.networkDisabled">
                        Network disabled
                    </b-form-checkbox>

                        <description-popover hug-text>
                            Only turn this option off if you want students' code to access the
                            internet.
                        </description-popover>
                </b-form-fieldset>
            </div>
        </collapse>

        <template slot="modal-footer">
            <b-button-toolbar justify style="width: 100%;">
                <submit-button variant="danger"
                               confirm="Are you sure you want to delete the tests for this category?"
                               :submit="() => internalValue.delete()"
                               @after-success="deleteSuite"
                               label="Delete"/>
                <submit-button
                    variant="outline-danger"
                    :disabled="value.isEmpty()"
                    label="Cancel"
                    :submit="cancelEdit"
                    confirm="Are you sure? Cancelling will lose all your changes."/>
                <submit-button :submit="saveSuite"
                               @success="afterSaveSuite"
                               label="Save">
                    <div slot="error"
                         slot-scope="scope"
                         class="text-left">
                        <template v-for="err in scope.error.messages.general">
                            {{ err }}
                        </template>

                        <template v-if="scope.error.messages.steps.length > 0">
                            Some steps are not valid:

                            <ul class="m-0 pl-3">
                                <li v-for="[step, errs], i in scope.error.messages.steps"
                                    v-if="errs.length > 0">
                                    {{ $utils.withOrdinalSuffix(i + 1) }} step<span v-if="step.name">
                                    with name <b>{{ step.name }}</b></span>:

                                    <ul class="m-0 pl-3">
                                        <li v-for="err in errs">{{ err }}</li>
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
        <b-card-header class="suite-header d-flex align-items-center">
            <span class="title">
                <a v-if="result"
                   href="#"
                   @click.capture.prevent.stop="$root.$emit('open-rubric-category', value.rubricRow.id)">
                    {{ value.rubricRow.header }}
                </a>
                <template v-else>
                    {{ value.rubricRow.header }}
                </template>
            </span>

            <a href="#"
               :id="optionsPopoverId"
               @click.stop.prevent>
                <small>Options</small>
            </a>

            <b-popover :target="optionsPopoverId" triggers="click">
                <table class="text-left">
                    <tr>
                        <td class="pr-3">
                            Timeout per step (seconds)
                        </td>
                        <td>
                            <span class="float-right">
                                {{ value.commandTimeLimit }}
                            </span>
                        </td>
                    </tr>

                    <tr>
                        <td>
                            Network disabled
                        </td>
                        <td>
                            <b-form-checkbox name="network-disabled"
                                             class="mr-0 readably-disabled float-right"
                                             disabled
                                             v-model="value.networkDisabled"/>
                        </td>
                    </tr>
                </table>
            </b-popover>

            <div v-if="editable || result"
                 class="sep ml-3"/>

            <div v-if="editable"
                 class="pencil ml-3"
                 @click="editSuite">
                <icon name="pencil"/>
            </div>

            <div v-else-if="result"
                 class="percentage ml-3">
                {{ pointPercentage }} %
            </div>
        </b-card-header>

        <table class="table mb-0">
            <thead :key="-1">
                <tr>
                    <th></th>
                    <th>No</th>
                    <th>Summary</th>
                    <th>
                        <template v-if="result">Score</template>
                        <template v-else>Weight</template>
                    </th>
                    <th v-if="result">Pass</th>
                </tr>
            </thead>

            <auto-test-step v-for="step, i in value.steps"
                            :value="step"
                            :test-types="stepTypes"
                            :key="step.trackingId"
                            :index="i + 1"
                            :result="result"
                            :is-continuous="isContinuous"
                            :assignment="assignment" />
        </table>
    </b-card>
</div>
</template>

<script>
import { mapActions } from 'vuex';
import { SlickList, SlickItem, HandleDirective } from 'vue-slicksort';

import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/bars';
import 'vue-awesome/icons/pencil';
import 'vue-awesome/icons/minus-square';
import 'vue-awesome/icons/plus-square';
import 'vue-awesome/icons/caret-down';

import { getProps } from '@/utils';

import Collapse from './Collapse';
import SubmitButton from './SubmitButton';
import AutoTestStep from './AutoTestStep';
import DescriptionPopover from './DescriptionPopover';

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
        isContinuous: {
            type: Boolean,
            default: false,
        },
    },

    data() {
        const id = this.$utils.getUniqueId();

        return {
            showModal: false,
            internalValue: null,
            slickItemMoving: false,

            optionsPopoverId: `options-${id}`,
            timeoutId: `timeout-${id}`,
            advancedOptionsCollapsed: true,
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
        permissions() {
            return this.$utils.getProps(this, {}, 'assignment', 'course', 'permissions');
        },

        disabledCategories() {
            return this.otherSuites.reduce((res, other) => {
                if (other.id !== this.internalValue.id) {
                    res[other.rubricRow.id] = other;
                }
                return res;
            }, {});
        },

        stepTypes() {
            return [
                {
                    name: 'io_test',
                    title: 'IO Test',
                    color: '#E7EEE9',
                    help: 'Give input to a program and match it to a given output.',
                },
                {
                    name: 'run_program',
                    title: 'Run Program',
                    color: '#E6DCCD',
                    help: 'Execute a program or bash command.',
                },
                {
                    name: 'custom_output',
                    title: 'Capture Points',
                    color: '#DFD3AA',
                    help: 'Execute a custom test program that outputs a value between 0 and 1.',
                },
                {
                    name: 'check_points',
                    title: 'Checkpoint',
                    color: '#D6CE5B',
                    help:
                        'Stop testing this category if the amount of points is below a certain threshold.',
                    meta: true,
                },
            ];
        },

        rubricRow() {
            return getProps(this, null, 'internalValue', 'rubricRow');
        },

        pointPercentage() {
            const result = this.$utils.getProps(this.result, null, 'suiteResults', this.value.id);
            const perc = this.$utils.getProps(result, null, 'percentage');

            return perc == null ? '-' : perc.toFixed(0);
        },

        expandedSteps() {
            return this.internalValue.steps.filter(s => !s.collapsed);
        },
    },

    methods: {
        ...mapActions('autotest', {
            storeDeleteAutoTestSuite: 'deleteAutoTestSuite',
            storeUpdateAutoTestSuite: 'updateAutoTestSuite',
        }),

        async createTestStep(type) {
            const res = {
                name: '',
                type,
                weight: 1,
                collapsed: false,
                hidden: false,
                data: {},
            };

            switch (type) {
                case 'io_test':
                    res.data.inputs = [
                        {
                            name: '',
                            args: '',
                            stdin: '',
                            output: '',
                            options: ['case', 'substring', 'trailing_whitespace'],
                            weight: 1,
                        },
                    ];
                    break;
                case 'custom_output':
                    res.data.regex = '\\f';
                    break;
                case 'check_points':
                    res.weight = 0;
                    res.data.min_points = 0;
                    break;
                case 'run_program':
                    res.data.program = '';
                    break;
                default:
                    throw new Error('Unknown test type!');
            }

            this.internalValue.addStep(res);
        },

        editSuite() {
            this.internalValue = this.value.copy();
            this.internalValue.steps.forEach(val => {
                val.collapsed = true;
            });
            this.showModal = true;
        },

        async afterSaveSuite() {
            this.$refs.editModal.hide();
            await this.$nextTick();
            this.$emit('input', this.internalValue);
            this.internalValue = null;
        },

        saveSuite() {
            return this.internalValue.save();
        },

        cancelEdit() {
            const modal = this.$refs.editModal;
            if (modal) {
                modal.hide();
                this.$emit('save-cancelled');
            }
        },

        deleteSuite() {
            return this.storeDeleteAutoTestSuite({
                autoTestId: this.autoTestId,
                autoTestSuite: this.internalValue,
            });
        },

        setRubricRow(cat) {
            this.$set(this.internalValue, 'rubricRow', cat);
        },

        toggleAllSteps() {
            const doExpand = this.expandedSteps.length === 0;
            this.internalValue.steps.forEach(step => {
                step.collapsed = !doExpand;
            });
        },
    },

    components: {
        Icon,
        Collapse,
        SubmitButton,
        SlickItem,
        SlickList,
        AutoTestStep,
        DescriptionPopover,
    },

    directives: {
        handle: HandleDirective,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.slick-item {
    overflow: hidden;
    z-index: 99999;

    &.no-text-select {
        user-select: none;
        cursor: grabbing !important;
    }

    .drag-handle {
        cursor: grab;

        &.disabled-handle {
            cursor: not-allowed;
            color: @text-color-dark;
        }
    }
}

.add-step-btn {
    color: rgba(0, 0, 0, 0.5) !important;
    border-color: rgba(0, 0, 0, 0.125) !important;

    &:hover {
        filter: brightness(95%);
    }
}

.dropdown-item {
    padding: 0;

    .rubric-description {
        white-space: initial;
        max-height: 5rem;
        display: block;
        overflow-y: auto;
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

.collapse-handle {
    cursor: pointer;

    .fa-icon {
        position: relative;
        top: 2px;
        margin-right: 0.5rem;
        transition: transform @transition-duration;
    }

    .x-collapsing & .fa-icon,
    .x-collapsed & .fa-icon {
        transform: rotate(-90deg);
    }
}

.expand-all-btn {
    cursor: pointer;
    opacity: 0.8;

    &:hover {
        opacity: 1;
    }
}

.suite-header {
    .title {
        flex: 1 1 auto;
    }

    > :not(.title) {
        flex: 0 0 auto;
    }

    .sep {
        width: 3px;
        height: 3px;
        border-radius: 50%;
        background-color: rgba(0, 0, 0, 0.4);
    }

    .pencil {
        cursor: pointer;
        transform: translateY(2px);
    }
}

.step-enter-active,
.step-leave-active {
    transition: all @transition-duration;
}

.step-enter,
.step-leave-to {
    opacity: 0;
    max-height: 0;
}

.step-enter-to,
.step-leave {
    max-height: 10rem;
    opacity: 1;
}
</style>

<style lang="less">
.auto-test-suite {
    .edit-suite-modal .modal-dialog {
        max-width: 891px;
    }

    .category-dropdown {
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
}
</style>
