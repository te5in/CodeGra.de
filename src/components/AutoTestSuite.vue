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
                                 @click="setRubricRow(cat)"
                                 :active="internalValue.rubricRow.id === cat.id" >
                    <div v-b-popover.top.hover="disabledCategories[cat.id] ? 'This rubric category is already in use.' : ''"
                         class="category-wrapper">
                        <h5>{{ cat.header }}</h5>
                        <span class="rubric-description">{{ cat.description }}</span>
                    </div>
                </b-dropdown-item>
            </b-dropdown>
        </b-input-group>

        <hr/>

        <h5 class="text-center mb-3">Steps</h5>

        <p v-if="internalValue.steps.length === 0" class="text-muted font-italic py-2">
            This category contains no steps. Please add some using the buttons
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
                    <span v-handle class="drag-handle text-muted">
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

        <div class="add-step-btns-wrapper">
            <b-button-toolbar class="m-auto">
                <b-btn v-for="stepType in stepTypes"
                       :key="stepType.value"
                       @click="internalValue.addStep(createTestStep(stepType.name))"
                       class="add-step-btn text-muted"
                       :style="{ 'background-color': stepType.color }"
                       v-b-popover.top.hover="stepType.help">
                    <icon name="plus" /> {{ stepType.title }}
                </b-btn>
            </b-button-toolbar>
        </div>

        <hr />

        <div class="advanced-options-collapse">
            <p class="collapse-handle mb-2 text-muted" v-b-toggle="advancedOptionsCollapseId">
                <icon name="caret-right" />
                Advanced options
            </p>

            <b-collapse :id="advancedOptionsCollapseId">
                <b-form-group label="Timeout per step in seconds">
                    <input class="form-control"
                            type="number"
                            min="0"
                            step="30"
                            v-model="internalValue.commandTimeLimit" />
                </b-form-group>

                <b-form-group>
                    <b-form-checkbox name="network-disabled"
                                     v-model="internalValue.networkDisabled">
                        Network disabled: tests do not have internet access.
                    </b-form-checkbox>
                </b-form-group>
            </b-collapse>
        </div>

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
                         class="custom-error-popover">
                        <template v-for="err in scope.error.messages.general">
                            {{ err }}
                        </template>

                        <template v-if="scope.error.messages.steps.length > 0">
                            Some steps are not valid:
                            <ul>
                                <li v-for="[step, errs], i in scope.error.messages.steps"
                                    :key="step.id"
                                    v-if="errs.length > 0">
                                    {{ $utils.withOrdinalSuffix(i + 1) }} step<span v-if="step.name">
                                        with name "{{ step.name }}"</span>:
                                    <ul>
                                        <li v-for="err in errs" :key="err">
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

    <b-card no-body v-if="value.isValid()">
        <div slot="header" class="title title-display">
            <a v-if="result"
               href="#"
               @click.capture.prevent.stop="$root.$emit('open-rubric-category', value.rubricRow.id)">
                {{ value.rubricRow.header }}
            </a>
            <span v-else>
                {{ value.rubricRow.header }}
            </span>

            <div v-if="editable"
                 class="pencil"
                 @click="editSuite">
                <icon name="pencil"/>
            </div>

            <div v-else-if="result">
                {{ pointPercentage }} %
            </div>
        </div>

        <div class="suite-steps">
            <table class="table steps-table">
                <thead>
                    <tr>
                        <th v-if="result"></th>
                        <th>No</th>
                        <th>Summary</th>
                        <th>
                            <template v-if="result">Score</template>
                            <template v-else>Weight</template>
                        </th>
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
import { mapActions } from 'vuex';
import { SlickList, SlickItem, HandleDirective } from 'vue-slicksort';

import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/bars';
import 'vue-awesome/icons/times';
import 'vue-awesome/icons/check';
import 'vue-awesome/icons/pencil';

import { getProps, getUniqueId } from '@/utils';

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
        const id = this.$utils.getUniqueId();

        return {
            showModal: false,
            internalValue: null,
            slickItemMoving: false,

            advancedOptionsCollapseId: `advanced-options-collapse-${id}`,
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
                    help: 'IO test!',
                },
                {
                    name: 'run_program',
                    title: 'Run Program',
                    color: '#E6DCCD',
                    help: 'Run program!',
                },
                {
                    name: 'custom_output',
                    title: 'Capture Points',
                    color: '#DFD3AA',
                    help: 'Capture points!',
                },
                {
                    name: 'check_points',
                    title: 'Check Points',
                    color: '#D6CE5B',
                    help: 'Check points test!',
                    meta: true,
                },
            ];
        },

        rubricRow() {
            return getProps(this, null, 'internalValue', 'rubricRow');
        },

        pointPercentage() {
            const result = this.result.suiteResults[this.value.id];
            return result == null || result.achieved == null || result.possible == null
                ? 0
                : (100 * result.achieved / result.possible).toFixed(0);
        },
    },

    methods: {
        ...mapActions('autotest', {
            storeDeleteAutoTestSuite: 'deleteAutoTestSuite',
            storeUpdateAutoTestSuite: 'updateAutoTestSuite',
        }),

        createTestStep(type) {
            const res = {
                name: '',
                type,
                weight: 1,
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
                            options: ['case', 'substring', 'trailing_whitespace'],
                            weight: 1,
                        },
                    ];
                    break;
                case 'custom_output':
                    res.data.regex = '((?:-\\s*)?1(?:\\.0*)?|0(?:\\.\\d*)?)';
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

            return res;
        },

        editSuite() {
            this.internalValue = this.value.copy();
            this.internalValue.steps.forEach(val => {
                val.opened = false;
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
                autoTestSuite: this.value,
            });
        },

        setRubricRow(cat) {
            this.$set(this.internalValue, 'rubricRow', cat);
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

.drag-handle {
    display: block;
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
    display: flex;
    align-items: center;

    label {
        margin-right: 0.5rem;
        margin-bottom: 0;
    }

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

.steps-table {
    margin-bottom: 0;
}

.advanced-options-collapse {
    .collapse-handle {
        cursor: pointer;

        .fa-icon {
            position: relative;
            top: 2px;
            margin-right: 0.5rem;
            transition: transform 300ms;
        }

        &:not(.collapsed) .fa-icon {
            transform: rotate(90deg);
        }
    }

    fieldset:last-child {
        margin-bottom: 0;
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
