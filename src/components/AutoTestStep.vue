<template>
<div class="auto-test-step"
     v-if="editable">
    <b-card no-body>
        <div class="step-header">
            <div v-b-toggle="collapseId"
                 class="collapse-toggle header-item"
                 :class="value.opened ? 'collapse-open' : ''">
                <icon name="chevron-down" :scale="0.75"/>
            </div>
            <div class="step-type header-item"
                 :style="{ 'background-color': typeColor }">
                {{ typeTitle }}
            </div>
            <b-input-group prepend="Name"
                           class="name-input header-item">
                <input class="form-control"
                       ref="nameInput"
                       :value="value.name"
                       @input="updateName($event.target.value)"/>
            </b-input-group>
            <b-input-group prepend="Weight"
                           class="points-input header-item"
                           v-b-popover.top.hover="weightPopoverText">
                <input class="form-control"
                       type="number"
                       :disabled="!hasWeight"
                       :value="value.weight"
                       @input="updateValue('weight', $event.target.value)"/>
            </b-input-group>

            <b-button-group class="header-item">
                <b-btn class="hide-header" :variant="value.hidden ? 'primary' : 'secondary'"
                    @click="updateHidden(!value.hidden)"
                    v-b-popover.top.hover="'Should the contents of this test be hidden from the student?'">
                    <icon :name="value.hidden ? 'eye-slash' : 'eye'"/>
                </b-btn>

                <submit-button
                    :disabled="disableDelete"
                    class="delete-btn"
                    :submit="() => null"
                    :wait-at-least="0"
                    v-b-popover.top.hover="'Delete this step'"
                    @after-success="$emit('delete')"
                    confirm="Are you sure you want to delete this step?"
                    variant="danger">
                    <icon name="times"/>
                </submit-button>
            </b-button-group>
        </div>

        <b-collapse :visible="value.opened"
                    @input="updateCollapse"
                    :id="collapseId"
                    v-if="!value.metatest">
            <div class="io-test-wrapper card-body">
                <template v-if="!stepType.meta">
                    <label :for="programNameId">
                        Program to test
                    </label>
                    <input class="form-control"
                           :value="value.data.program"
                           :id="programNameId"
                           @input="updateValue('program', $event.target.value)"/>
                </template>
                <template v-else-if="value.type === 'check_points'">
                    <label>
                        Stop test suite if amount of points is below
                    </label>
                    <input class="form-control min-points-input"
                           type="number"
                           :value="value.data.min_points"
                           @input="updateValue('min_points', $event.target.value)"/>
                </template>

                <template v-if="value.type === 'capture_points'">
                    <hr/>

                    <label :for="regexId">
                        Regex that matches one grade in the first capture group
                        <description-popover hug-text>
                            This regex will be applied line by line, starting
                            from the <b>last</b> line. The regex should be
                            a <i>Python</i> regex line. The first capture group
                            should capture a valid python float, the default
                            regex captures a single float.
                        </description-popover>
                    </label>
                    <input :value="value.data.regex"
                           :id="regexId"
                           class="form-control"
                           @input="updateValue('regex', $event.target.value)">
                </template>
                <template v-else-if="value.type === 'io_test'">
                    <hr/>

                    <div v-for="input, index in inputs"
                         :key="input.id">
                        <div class="io-input-wrapper">
                            <div class="left-column column">
                                <b-form-fieldset>
                                    <label :for="inputNameId(index)">Name</label>
                                    <input class="form-control arg-input"
                                           :id="inputNameId(index)"
                                           :value="input.name"
                                           @input="updateInput(index, 'name', $event.target.value)"/>
                                </b-form-fieldset>

                                <b-form-fieldset>
                                    <label :for="argsId(index)">Input arguments</label>
                                    <input class="form-control arg-input"
                                           :id="argsId"
                                           :value="input.args"
                                           @input="updateInput(index, 'args', $event.target.value)"/>
                                </b-form-fieldset>

                                <div class="stdin-wrapper">
                                    <label :for="stdinId(index)">Input</label>
                                    <textarea class="form-control stdin-input"
                                              :value="input.stdin"
                                              :id="stdinId"
                                              rows="2"
                                              @input="updateInput(index, 'stdin', $event.target.value)"/>
                                </div>
                            </div>
                            <div class="right-column column">
                                <label :for="optionsId(index)">
                                    Options
                                </label>
                                <b-form-checkbox-group :checked="input.options"
                                                       :options="ioOptions"
                                                       :id="optionsId(index)"
                                                       class="io-options"
                                                       @input="updateInput(index, 'options', $event)"/>
                                <label :for="stdoutId(index)">Expected output</label>
                                <textarea class="form-control expected-output"
                                          :value="input.output"
                                          rows="4"
                                          :id="stdoutId"
                                          @input="updateInput(index, 'output', $event.target.value)"/>
                            </div>
                        </div>

                        <div class="footer-wrapper">
                            <div v-b-toggle="collapseAdvancedId(index)"
                                 class="collapse-toggle"
                                 :class="collapseState[index] ? 'collapse-open' : ''">
                                <icon name="caret-down"/>
                                Advanced
                            </div>
                            <b-btn variant="danger"
                                   v-b-popover.top.hover="'Delete this input and output case.'"
                                   @click="deleteInput(index)"
                                   :disabled="value.data.inputs.length < 2">
                                <icon name="times"/>
                            </b-btn>
                        </div>
                        <b-collapse :id="collapseAdvancedId(index)"
                                    class="advanced-collapse"
                                    v-model="collapseState[index]">
                            <div class="step-footer">
                                <b-form-fieldset>
                                    <label :for="weightId(index)">
                                        Weight
                                    </label>
                                    <input class="form-control weight-input"
                                           :id="weightId(index)"
                                           type="number"
                                           :value="input.weight"
                                           @input="updateInput(index, 'weight', $event.target.value)"/>
                                </b-form-fieldset>
                            </div>
                        </b-collapse>

                        <hr/>
                    </div>

                    <div class="add-input-btn-wrapper">
                        <b-btn class="add-input-btn"
                            v-b-popover.top.hover="'Add another input and output case.'"
                            @click="addInput">
                            <icon name="plus"/>
                        </b-btn>
                    </div>
                </template>
            </div>
        </b-collapse>
    </b-card>
</div>
<!-- Not editable -->
<tbody v-else class="auto-test-step" :class="{ 'with-output': canViewOutput }">
    <template v-if="value.type === 'check_points'">
        <tr class="step-summary" v-b-toggle="resultsCollapseId">
            <td class="expand" v-if="result">
                <icon v-if="canViewOutput" name="chevron-down" :scale="0.75" />
                <icon v-else-if="value.hidden" name="eye-slash" :scale="0.85"
                        v-b-popover.hover.top="'You cannot view this step\'s results.'" />
            </td>
            <td class="index">{{ index }}</td>
            <td class="summary" colspan="2">
                <b>{{ stepName }}</b>
                Stop when you got less than {{ value.data.min_points }} points.
            </td>
            <td class="passed" v-if="result">
                <auto-test-state :state="stepResult.state" />
            </td>
        </tr>

        <tr v-if="canViewOutput" class="results-log-collapse-row">
            <td colspan="5">
                <b-collapse :id="resultsCollapseId" class="container-fluid">
                    <div class="row">
                        <div class="col-12">
                            <span>
                                Exit status code:
                                <code>{{ getProps(stepResult.log, '(unknown)', 'exit_code') }}</code>
                            </span>
                        </div>

                        <div class="col-6">
                            <label>Output</label>
                            <pre class="form-control">{{ stepResult.log.stdout }}</pre>
                        </div>

                        <div class="col-6">
                            <label>Errors</label>
                            <pre class="form-control">{{ stepResult.log.stderr }}</pre>
                        </div>
                    </div>
                </b-collapse>
            </td>
        </tr>
    </template>

    <template v-else-if="value.type === 'run_program'">
        <tr class="step-summary" v-b-toggle="resultsCollapseId">
            <td class="expand" v-if="result">
                <icon v-if="canViewOutput" name="chevron-down" :scale="0.75" />
                <icon v-else-if="value.hidden" name="eye-slash" :scale="0.85"
                        v-b-popover.hover.top="'You cannot view this step\'s results.'" />
            </td>
            <td class="index">{{ index }}</td>
            <td class="summary">
                <b>{{ stepName }}</b>
                Run <code>{{ value.data.program }}</code> and check for successful completion.
            </td>
            <td class="weight">{{ value.weight }}</td>
            <td class="passed" v-if="result">
                <auto-test-state :state="stepResult.state" />
            </td>
        </tr>

        <tr v-if="canViewOutput" class="results-log-collapse-row">
            <td colspan="5">
                <b-collapse :id="resultsCollapseId" class="container-fluid">
                    <div class="row">
                        <div class="col-12">
                            <span>
                                Exit status code:
                                <code>{{ getProps(stepResult.log, '(unknown)', 'exit_code') }}</code>
                            </span>
                        </div>

                        <div class="col-6">
                            <label>Output</label>
                            <pre class="form-control">{{ stepResult.log.stdout }}</pre>
                        </div>

                        <div class="col-6">
                            <label>Errors</label>
                            <pre class="form-control">{{ stepResult.log.stderr }}</pre>
                        </div>
                    </div>
                </b-collapse>
            </td>
        </tr>
    </template>

    <template v-else-if="value.type === 'capture_points'">
        <tr class="step-summary" v-b-toggle="resultsCollapseId">
            <td class="expand" v-if="result">
                <icon v-if="canViewOutput" name="chevron-down" :scale="0.75" />
                <icon v-else-if="value.hidden" name="eye-slash" :scale="0.85"
                        v-b-popover.hover.top="'You cannot view this step\'s results.'" />
            </td>
            <td class="index">{{ index }}</td>
            <td class="summary">
                <b>{{ stepName }}</b>
                Run <code>{{ value.data.program }}</code> and parse its output.
            </td>
            <td class="weight">{{ value.weight }}</td>
            <td class="passed" v-if="result">
                <auto-test-state :state="stepResult.state" />
            </td>
        </tr>

        <tr v-if="canViewOutput" class="results-log-collapse-row">
            <td colspan="5">
                <b-collapse :id="resultsCollapseId" class="container-fluid">
                    <div class="row">
                        <div class="col-12">
                            <label>
                                Match output on
                                <code>{{ value.data.regex }}</code>
                            </label>
                            <label>
                                Exit status code:
                                <code>{{ getProps(stepResult.log, '(unknown)', 'exit_code') }}</code>
                            </label>
                        </div>

                        <div class="col-6">
                            <label>Output</label>
                            <pre class="form-control">{{ stepResult.log.stdout }}</pre>
                        </div>

                        <div class="col-6">
                            <label>Errors</label>
                            <pre class="form-control">{{ stepResult.log.stderr }}</pre>
                        </div>
                    </div>
                </b-collapse>
            </td>
        </tr>
    </template>

    <template v-else-if="value.type === 'io_test'">
        <tr>
            <td class="expand" v-if="result">
                <icon v-if="value.hidden" name="eye-slash" :scale="0.85"
                    v-b-popover.hover.top="'You cannot view this step\'s results.'" />
            </td>
            <td class="index"><b>{{ index }}</b></td>
            <td class="summary">
                <b>{{ stepName }}</b>
                Run <code>{{ value.data.program }}</code> and match its output to an expected value.
            </td>
            <td class="weight"><b>{{ value.weight }}</b></td>
            <td class="passed" v-if="result"></td>
        </tr>

        <template v-for="input, i in inputs">
            <tr class="step-summary" v-b-toggle="`${resultsCollapseId}-${i}`">
                <td class="expand" v-if="result">
                    <icon v-if="canViewOutput" name="chevron-down" :scale="0.75" />
                    <icon v-else-if="value.hidden" name="eye-slash" :scale="0.85"
                        v-b-popover.hover.top="'You cannot view this step\'s results.'" />
                </td>
                <td class="index">{{ index }}.{{ i + 1 }}</td>
                <td class="summary">{{ input.name }}</td>
                <td class="weight">{{ input.weight }}</td>
                <td class="passed" v-if="result">
                    <auto-test-state :state="stepResult.log ? stepResult.log.steps[i].state : 'skipped'" />
                </td>
            </tr>

            <tr v-if="canViewOutput"
                class="results-log-collapse-row">
                <td colspan="5">
                    <b-collapse :id="`${resultsCollapseId}-${i}`">
                        <b-card no-body style="border: 0;">
                            <b-tabs card no-fade class="container-fluid">
                                <b-tab title="Output" class="row">
                                    <div class="col-6">
                                        <label>Expected output</label>
                                        <pre class="form-control">{{ input.output }}</pre>
                                    </div>

                                    <div class="col-6">
                                        <label>Actual output</label>
                                        <pre class="form-control">{{ stepResult.log.steps[i].stdout }}</pre>
                                    </div>
                                </b-tab>

                                <b-tab title="Input" class="row">
                                    <div class="col-6">
                                        <label>Input arguments</label>
                                        <code class="form-control">{{ input.args }}</code>

                                        <label>Options</label>
                                        <b-form-checkbox-group
                                            :options="ioOptions"
                                            :checked="input.options"
                                            @click.native.capture.prevent.stop/>
                                    </div>

                                    <div class="col-6">
                                        <label>Input</label>
                                        <pre class="form-control">{{ input.stdin }}</pre>
                                    </div>
                                </b-tab>

                                <b-tab title="Errors" class="row" v-if="stepResult.log.steps[i].stderr">
                                    <div class="col-12">
                                        <label>Errors</label>
                                        <pre class="form-control">{{ stepResult.log.steps[i].stderr }}</pre>
                                    </div>
                                </b-tab>
                            </b-tabs>
                        </b-card>
                    </b-collapse>
                </td>
            </tr>
        </template>
    </template>
</tbody>
</template>

<script>
import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/check';
import 'vue-awesome/icons/times';
import 'vue-awesome/icons/eye';
import 'vue-awesome/icons/eye-slash';
import 'vue-awesome/icons/files-o';
import 'vue-awesome/icons/plus';
import 'vue-awesome/icons/caret-down';
import 'vue-awesome/icons/chevron-down';
import 'vue-awesome/icons/clock-o';
import 'vue-awesome/icons/ban';

import { getUniqueId, deepCopy, getProps } from '@/utils';

import SubmitButton from './SubmitButton';
import DescriptionPopover from './DescriptionPopover';
import AutoTestState from './AutoTestState';

export default {
    name: 'auto-test-step',

    props: {
        value: {
            type: Object,
            required: true,
        },

        index: {
            type: Number,
            required: true,
        },

        editable: {
            type: Boolean,
            default: false,
        },

        disableDelete: {
            type: Boolean,
            default: false,
        },

        testTypes: {
            type: Array,
            required: true,
        },

        result: {
            type: Object,
            default: null,
        },
    },

    data() {
        const id = getUniqueId();

        return {
            getProps,
            id,
            collapseState: {},
            mainCollapseState: this.collapseOpen,
            autoTestStepModalId: `auto-test-step-modal-${id}`,
        };
    },

    watch: {
        editable() {
            this.collapseState = {};
        },
    },

    computed: {
        type() {
            return this.testTypes.find(x => x.name === this.value.type);
        },

        typeTitle() {
            return this.type.title;
        },

        typeColor() {
            return this.type.color;
        },

        stepName() {
            return this.value.name;
        },

        programNameId() {
            return `auto-test-step-program-${this.id}`;
        },

        collapseId() {
            return `auto-test-step-main-collapse-${this.id}`;
        },

        inputNameId() {
            return n => `auto-test-step-input-name-${this.id}-${n}`;
        },

        argsId() {
            return n => `auto-test-step-args-${this.id}-${n}`;
        },

        stdinId() {
            return n => `auto-test-step-stdin-${this.id}-${n}`;
        },

        stdoutId() {
            return n => `auto-test-step-stdout-${this.id}-${n}`;
        },

        regexId() {
            return `auto-test-step-prefix-${this.id}`;
        },

        collapseAdvancedId() {
            return n => `auto-test-step-advanced-${this.id}-${n}`;
        },

        optionsId() {
            return n => `auto-test-step-options-${this.id}-${n}`;
        },

        weightId() {
            return n => `auto-test-step-weight-${this.id}-${n}`;
        },

        resultsCollapseId() {
            return `auto-test-step-result-collapse-${this.id}`;
        },

        stepType() {
            const type = this.value.type;
            return this.testTypes.find(t => t.name === type);
        },

        hasWeight() {
            return !this.stepType.meta && this.value.type !== 'io_test';
        },

        ioOptions() {
            return [
                { text: 'Case insensitive', value: 'case' },
                { text: 'Ignore trailing whitespace', value: 'trailing_whitespace' },
                { text: 'Substring', value: 'substring' },
                { text: 'Regex', value: 'regex' },
            ];
        },

        inputs() {
            return getProps(this, [], 'value', 'data', 'inputs');
        },

        weightPopoverText() {
            if (this.value.type === 'io_test') {
                return 'This is equal to the sum of the weights of each input.';
            } else if (this.stepType.meta) {
                return 'This step does not count towards the score and thus has no weight.';
            } else {
                return '';
            }
        },

        stepResult() {
            return getProps(this, null, 'result', 'stepResults', this.value.id);
        },

        canViewOutput() {
            if (!this.stepResult) {
                return false;
            }

            const { state, log } = this.stepResult;

            // TODO: Check can_view_autotest_output permission
            return (state === 'passed' || state === 'failed') && log != null && !this.value.hidden;
        },
    },

    mounted() {
        if (this.editable && this.$refs.nameInput && !this.value.name) {
            this.$refs.nameInput.focus();
        }
    },

    methods: {
        updateInput(index, key, value) {
            const input = [...this.inputs];
            input[index] = {
                ...input[index],
                [key]: value,
            };
            this.updateValue('inputs', input);
        },

        createInput() {
            return {
                name: '',
                args: '',
                stdin: '',
                output: '',
                options: [],
                weight: 1,
            };
        },

        addInput() {
            this.updateValue('inputs', [...this.inputs, this.createInput()]);
        },

        deleteInput(index) {
            this.updateValue('inputs', this.inputs.filter((_, i) => i !== index));
        },

        updateName(name) {
            this.$emit('input', Object.assign(deepCopy(this.value), { name }));
        },

        updateHidden(hidden) {
            this.$emit('input', Object.assign(deepCopy(this.value), { hidden }));
        },

        updateCollapse(opened) {
            this.$emit('input', Object.assign(deepCopy(this.value), { opened }));
        },

        updateValue(key, value) {
            if (key === 'weight') {
                this.$emit(
                    'input',
                    Object.assign(deepCopy(this.value), {
                        weight: value,
                    }),
                );
                return;
            }

            let weight = this.value.weight;
            if (key === 'inputs') {
                weight = (value || []).reduce((res, cur) => res + Number(cur.weight), 0);
                if (Number.isNaN(weight)) {
                    weight = '-';
                }
            }

            this.$emit(
                'input',
                Object.assign(deepCopy(this.value), {
                    data: {
                        ...this.value.data,
                        [key]: value,
                    },
                    weight,
                }),
            );
        },
    },

    components: {
        Icon,
        SubmitButton,
        DescriptionPopover,
        AutoTestState,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.io-input-wrapper {
    display: flex;

    .column {
        flex: 1 1 50%;
        &:not(:last-child) {
            margin-right: 0.5rem;
        }
        &:not(:first-child) {
            margin-left: 0.5rem;
        }

        display: flex;
        flex-direction: column;

        .stdin-wrapper,
        .expected-output {
            flex: 1 1 auto;
            min-height: 3rem;
            display: flex;
            flex-direction: column;
        }
        .stdin-wrapper textarea {
            flex: 1 1 auto;
        }
    }
}

.expected-output {
    height: 100%;
}

.step-header {
    background-color: rgba(0, 0, 0, 0.03);
    display: flex;
    align-content: center;
    align-items: center;

    .header-item {
        margin: 0.25rem;
    }

    .hide-header {
        box-shadow: none;
    }

    .step-type {
        padding: 0.375rem 1rem;
        flex: 0 1 auto;
        color: @text-color-muted;
        border: 1px solid rgba(0, 0, 0, 0.125);
        border-radius: 0.25rem;
    }

    .name-input {
        border-radius: 0;
        flex: 1 1 18rem;
    }

    .points-input {
        flex: 0 1 12rem;
        .input-group-text,
        .form-control {
            border-left: 1px solid rgba(0, 0, 0, 0.125);
        }
    }

    .cur-prog-title {
        flex: 1;
        background-color: @footer-color;
        padding: 0.375rem 1rem;
        border-radius: 0.25rem;
        border: 1px solid rgba(0, 0, 0, 0.125);
    }
}

.step-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.25rem;
    background-color: rgba(0, 0, 0, 0.03);
    border: 1px solid rgba(0, 0, 0, 0.125);
    border-radius: 0.25rem;
    padding: 0.375rem 1rem;
}

hr {
    margin: 1rem 0;
}

.form-group,
.io-options {
    margin-bottom: 0.5rem;
}

.collapse-toggle {
    cursor: pointer;

    .fa-icon {
        transition: all 300ms linear;
        transform: rotate(-90deg);
    }

    &.collapse-open .fa-icon {
        transform: rotate(0deg);
    }

    &.header-item {
        padding: 0 1rem;
        display: flex;
    }
}

.min-points-input,
.weight-input {
    text-align: left;
}

.footer-wrapper {
    display: flex;
    flex-direction: row;
    align-items: end;
    justify-content: space-between;
    margin-top: 1rem;
    margin-bottom: 0.25rem;
}

.add-input-btn-wrapper {
    display: flex;
    justify-content: end;
}

.card-body {
    border-top: 1px solid rgba(0, 0, 0, 0.125);
}

.flex-padding-element {
    flex: 1 1 auto;
}

.table tbody {
    + tbody {
        border-top-width: 1px;
    }

    &.with-output .step-summary:hover {
        background-color: rgba(0, 0, 0, 0.03);
        cursor: pointer;
    }

    .step-summary {
        td:not(.expand) .fa-icon {
            transform: translateY(2px);
        }

        .expand .fa-icon {
            transition: transform 300ms;
        }

        &.collapsed .expand .fa-icon {
            transform: rotate(-90deg);
        }
    }

    td {
        &.expand,
        &.index,
        &.weight,
        &.passed {
            width: 1px;
            white-space: nowrap;
        }

        &.weight,
        &.passed {
            text-align: center;
        }
    }
}

.results-log-collapse-row {
    cursor: initial;

    &:hover {
        background-color: initial;
    }

    td {
        border-top: 0;
        padding: 0;
    }

    .row {
        margin-bottom: 1rem;
    }

    .col-6,
    .col-12 {
        display: flex;
        flex-direction: column;
    }

    code.form-control,
    pre.form-control {
        background-color: rgba(0, 0, 0, 0.03);
        margin-bottom: 1rem;

        &:last-child {
            margin-bottom: 0;
        }
    }

    code.form-control {
        flex: 0 0 auto;
    }

    pre.form-control {
        flex: 1 1 auto;
        max-height: 15rem;
        font-size: 87.5%;
    }
}
</style>

<style lang="less">
.auto-test-step .results-log-collapse-row {
    .card-header {
        background-color: inherit;
        border-bottom: 0;
    }

    .tab-pane {
        display: flex;
        padding: 0.75rem 0 0;
    }
}
</style>
