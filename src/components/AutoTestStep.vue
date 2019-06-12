<template>
<div class="auto-test-step" v-if="editable">
    <b-card no-body>
        <collapse :disabled="!canViewDetails"
                  :speed="500"
                  :collapsed="value.collapsed"
                  @change="updateCollapse"
                  :id="`step-collapse-${index}`">
            <b-card-header slot="handle" class="step-header p-1 d-flex align-items-center">
                <icon v-if="canViewDetails" :key="`collapse-toggle-${index}`" class="toggle mx-3" name="chevron-down" :scale="0.75" />
                <icon v-else class="mx-3" name="eye-slash" :scale="0.85" />

                <div class="step-type mr-1 btn"
                     :style="{ 'background-color': stepType.color }">
                    {{ stepType.title }}
                </div>

                <b-input-group prepend="Name"
                               class="name-input mr-1">
                    <input class="form-control"
                           ref="nameInput"
                           :value="value.name"
                           @click.stop
                           @input="updateName($event.target.value)"/>
                </b-input-group>

                <b-input-group prepend="Weight"
                               class="points-input mr-1"
                               v-b-popover.top.hover="weightPopoverText"
                               v-if="hasWeight">
                    <input class="form-control"
                           type="number"
                           :disabled="!hasWeight"
                           :value="value.weight"
                           @click.stop
                           @input="updateValue('weight', $event.target.value)"/>
                </b-input-group>

                <b-button-group>
                    <b-btn :variant="value.hidden ? 'primary' : 'secondary'"
                           @click.stop="updateHidden(!value.hidden)"
                           v-b-popover.top.hover="'Should the contents of this step be hidden from the student?'">
                        <icon :name="value.hidden ? 'eye-slash' : 'eye'"/>
                    </b-btn>

                    <submit-button :disabled="disableDelete"
                                   :submit="() => null"
                                   :wait-at-least="0"
                                   v-b-popover.top.hover="'Delete this step'"
                                   @after-success="$emit('delete')"
                                   confirm="Are you sure you want to delete this step?"
                                   variant="danger">
                        <icon name="times"/>
                    </submit-button>
                </b-button-group>
            </b-card-header>

            <b-card-body slot="content" v-if="canViewDetails">
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
                        Stop test category if amount of points is below
                    </label>

                    <input class="form-control text-left"
                           type="number"
                           :value="value.data.min_points"
                           @input="updateValue('min_points', $event.target.value)"/>
                </template>

                <template v-if="value.type === 'custom_output'">
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

                    <div v-for="input, index in inputs" :key="input.id">
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
                                            rows="4"
                                            @input="updateInput(index, 'stdin', $event.target.value)"/>
                                </div>
                            </div>
                            <div class="right-column column">
                                <label :for="optionsId(index)">Options</label>
                                <b-form-checkbox-group stacked
                                                       :checked="input.options"
                                                       :options="ioOptions"
                                                       :id="optionsId(index)"
                                                       class="form-control mb-3"
                                                       @input="updateInput(index, 'options', $event)"/>

                                <label :for="stdoutId(index)">Expected output</label>
                                <textarea class="form-control expected-output"
                                        :value="input.output"
                                        rows="4"
                                        :id="stdoutId"
                                        @input="updateInput(index, 'output', $event.target.value)"/>
                            </div>
                        </div>

                        <div class="footer-wrapper mt-3 mb-2 d-flex flex-row justify-content-between">
                            <div v-b-toggle="collapseAdvancedId(index)"
                                 class="collapse-toggle text-muted font-italic">
                                <icon name="caret-down" />
                                Advanced options
                            </div>

                            <b-btn variant="danger"
                                   v-b-popover.top.hover="'Delete this input and output case.'"
                                   @click="deleteInput(index)"
                                   :disabled="value.data.inputs.length < 2">
                                <icon name="times"/> Delete
                            </b-btn>
                        </div>

                        <b-collapse :id="collapseAdvancedId(index)"
                                    class="advanced-collapse"
                                    v-model="collapseState[index]">
                            <div class="p-3 bg-light border rounded">
                                <b-form-fieldset class="m-0">
                                    <b-input-group prepend="Weight">
                                        <input class="form-control text-left"
                                            :id="weightId(index)"
                                            type="number"
                                            :value="input.weight"
                                            @input="updateInput(index, 'weight', $event.target.value)"/>
                                    </b-input-group>
                                </b-form-fieldset>
                            </div>
                        </b-collapse>

                        <hr/>
                    </div>

                    <div class="add-input-btn-wrapper">
                        <b-btn class="add-input-btn"
                               @click="addInput"
                               v-b-popover.top.hover="'Add another input and output case.'">
                            <icon name="plus"/>
                        </b-btn>
                    </div>
                </template>
            </b-card-body>
        </collapse>
    </b-card>
</div>

<!-- Not editable -->
<tbody v-else class="auto-test-step">
    <template v-if="value.type === 'check_points'">
        <tr class="step-summary"
            :class="{ 'with-output': canViewOutput }"
            :key="resultsCollapseId"
            v-b-toggle="resultsCollapseId">
            <td class="expand shrink" v-if="result">
                <icon v-if="canViewOutput" name="chevron-down" :scale="0.75" />
                <icon v-else-if="!canViewDetails" name="eye-slash" :scale="0.85"
                      v-b-popover.hover.top="'You cannot view this step\'s details.'" />
            </td>
            <td class="shrink">{{ index }}</td>
            <td colspan="2">
                <b>{{ stepName }}</b>

                <template v-if="canViewDetails">
                    Stop when you achieve less than
                    <code>{{ value.data.min_points }}</code>
                    points.
                </template>
            </td>
            <td class="shrink text-center" v-if="result">
                <auto-test-state :result="stepResult" />
            </td>
        </tr>

        <tr v-if="canViewOutput" class="results-log-collapse-row">
            <td colspan="5">
                <b-collapse :id="resultsCollapseId" class="container-fluid">
                    <div class="row">
                        <div class="col-12">
                            You {{ stepResult.finished ? 'scored' : 'did not score' }}
                            enough points.
                        </div>
                    </div>
                </b-collapse>
            </td>
        </tr>
    </template>

    <template v-else-if="value.type === 'run_program'">
        <tr class="step-summary"
            :class="{ 'with-output': canViewOutput }"
            :key="resultsCollapseId"
            v-b-toggle="resultsCollapseId">
            <td class="expand shrink" v-if="result">
                <icon v-if="canViewOutput" name="chevron-down" :scale="0.75" />
                <icon v-else-if="!canViewDetails" name="eye-slash" :scale="0.85"
                        v-b-popover.hover.top="'You cannot view this step\'s details.'" />
            </td>
            <td class="shrink">{{ index }}</td>
            <td>
                <b>{{ stepName }}</b>

                <template v-if="canViewDetails">
                    Run <code>{{ value.data.program }}</code>
                    and check for successful completion.
                </template>
            </td>
            <td class="shrink text-center">
                <template v-if="result">
                    {{ achievedPoints }} /
                </template>
                {{ $utils.toMaxNDecimals(value.weight, 2) }}
            </td>
            <td class="shrink text-center" v-if="result">
                <auto-test-state :result="stepResult" />
            </td>
        </tr>

        <tr v-if="canViewOutput" class="results-log-collapse-row">
            <td colspan="5">
                <b-collapse :id="resultsCollapseId">
                    <b-card no-body>
                        <b-tabs card no-fade class="container-fluid">
                            <b-tab title="Info" class="row">
                                <p class="col-12">
                                    Exit code:
                                    <code>{{ $utils.getProps(stepResult.log, '(unknown)', 'exit_code') }}</code>
                                </p>
                            </b-tab>

                            <b-tab title="Output" class="row">
                                <div class="col-12">
                                    <inner-code-viewer class="rounded border"
                                                       :assignment="assignment"
                                                       :code-lines="stepStdout"
                                                       :file-id="-1"
                                                       :feedback="{}"
                                                       :start-line="0"
                                                       :show-whitespace="true"
                                                       :warn-no-newline="false" />
                                </div>
                            </b-tab>

                            <b-tab title="Errors" class="row" v-if="$utils.getProps(stepResult, null, 'log', 'stderr')">
                                <div class="col-12">
                                    <inner-code-viewer class="rounded border"
                                                       :assignment="assignment"
                                                       :code-lines="stepStderr"
                                                       :file-id="-1"
                                                       :feedback="{}"
                                                       :start-line="0"
                                                       :show-whitespace="true"
                                                       :warn-no-newline="false" />
                                </div>
                            </b-tab>
                        </b-tabs>
                    </b-card>
                </b-collapse>
            </td>
        </tr>
    </template>

    <template v-else-if="value.type === 'custom_output'">
        <tr class="step-summary"
            :class="{ 'with-output': canViewOutput }"
            :key="resultsCollapseId"
            v-b-toggle="resultsCollapseId">
            <td class="expand shrink" v-if="result">
                <icon v-if="canViewOutput" name="chevron-down" :scale="0.75" />
                <icon v-else-if="!canViewDetails" name="eye-slash" :scale="0.85"
                        v-b-popover.hover.top="'You cannot view this step\'s details.'" />
            </td>
            <td class="shrink">{{ index }}</td>
            <td>
                <b>{{ stepName }}</b>

                <template v-if="canViewDetails">
                    Run <code>{{ value.data.program }}</code> and parse its output.
                </template>
            </td>
            <td class="shrink text-center">
                <template v-if="result">
                    {{ achievedPoints }} /
                </template>
                {{ $utils.toMaxNDecimals(value.weight, 2) }}
            </td>
            <td class="shrink text-center" v-if="result">
                <auto-test-state :result="stepResult" />
            </td>
        </tr>

        <tr v-if="canViewOutput" class="results-log-collapse-row">
            <td colspan="5">
                <b-collapse :id="resultsCollapseId">
                    <b-card no-body>
                        <b-tabs card no-fade class="container-fluid">
                            <b-tab title="Info" class="row">
                                <p class="col-12" v-if="canViewDetails">
                                    Match output on:
                                    <code>{{ value.data.regex }}</code>
                                </p>
                                <p class="col-12">
                                    Exit code:
                                    <code>{{ $utils.getProps(stepResult.log, '(unknown)', 'exit_code') }}</code>
                                </p>
                            </b-tab>

                            <b-tab title="Output" class="row">
                                <div class="col-12">
                                    <inner-code-viewer class="rounded border"
                                                       :assignment="assignment"
                                                       :code-lines="stepStdout"
                                                       :file-id="-1"
                                                       :feedback="{}"
                                                       :start-line="0"
                                                       :show-whitespace="true"
                                                       :warn-no-newline="false" />
                                </div>
                            </b-tab>

                            <b-tab title="Errors" class="row" v-if="$utils.getProps(stepResult, null, 'log', 'stderr')">
                                <div class="col-12">
                                    <inner-code-viewer class="rounded border"
                                                       :assignment="assignment"
                                                       :code-lines="stepStderr"
                                                       :file-id="-1"
                                                       :feedback="{}"
                                                       :start-line="0"
                                                       :show-whitespace="true"
                                                       :warn-no-newline="false" />
                                </div>
                            </b-tab>
                        </b-tabs>
                    </b-card>
                </b-collapse>
            </td>
        </tr>
    </template>

    <template v-else-if="value.type === 'io_test'">
        <tr>
            <td class="expand shrink" v-if="result">
                <icon v-if="!canViewDetails" name="eye-slash" :scale="0.85"
                      v-b-popover.hover.top="'You cannot view this step\'s details.'" />
            </td>
            <td class="shrink"><b>{{ index }}</b></td>
            <td>
                <b>{{ stepName }}</b>

                <template v-if="canViewDetails">
                    Run <code>{{ value.data.program }}</code>
                    and match its output to an expected value.
                </template>
            </td>
                <td class="shrink text-center">
                    <template v-if="result">
                        {{ achievedPoints }} /
                    </template>
                    {{ $utils.toMaxNDecimals(value.weight, 2) }}
                </td>
            <td class="shrink text-center" v-if="result"></td>
        </tr>

        <template v-for="input, i in inputs">
            <tr class="step-summary"
                :class="{ 'with-output': canViewSubStepOutput(i) }"
                :key="`${resultsCollapseId}-${i}`"
                v-b-toggle="`${resultsCollapseId}-${i}`">
                <td class="expand shrink" v-if="result">
                    <icon v-if="canViewSubStepOutput(i)" name="chevron-down" :scale="0.75" />
                    <icon v-else-if="!canViewDetails" name="eye-slash" :scale="0.85"
                        v-b-popover.hover.top="'You cannot view this step\'s details.'" />
                </td>
                <td class="shrink">{{ index }}.{{ i + 1 }}</td>
                <td>{{ input.name }}</td>
                <td class="shrink text-center">
                    <template v-if="result">
                        {{ ioSubStepProps(i, '-', 'achieved_points') }} /
                    </template>
                    {{ $utils.toMaxNDecimals(input.weight, 2) }}
                </td>
                <td class="shrink text-center" v-if="result">
                    <auto-test-state :result="ioSubStepProps(i, null)" />
                </td>
            </tr>

            <tr v-if="canViewSubStepOutput(i)" class="results-log-collapse-row">
                <td colspan="5">
                    <b-collapse :id="`${resultsCollapseId}-${i}`">
                        <b-card no-body>
                            <b-tabs card no-fade class="container-fluid">
                                <b-tab title="Output" class="row">
                                    <p v-if="ioSubStepProps(i, '', 'exit_code')" class="col-12">
                                        <label>Exit code:</label>
                                        <code>{{ ioSubStepProps(i, '', 'exit_code') }}</code>
                                    </p>

                                    <div class="col-6">
                                        <label>Expected output:</label>
                                        <inner-code-viewer class="rounded border"
                                                           :assignment="assignment"
                                                           :code-lines="prepareOutput(input.output)"
                                                           :file-id="-1"
                                                           :feedback="{}"
                                                           :start-line="0"
                                                           :show-whitespace="true"
                                                           :warn-no-newline="false" />
                                    </div>

                                    <div class="col-6">
                                        <label>Actual output:</label>
                                        <inner-code-viewer class="rounded border"
                                                           :assignment="assignment"
                                                           :code-lines="prepareOutput(ioSubStepProps(i, '', 'stdout'))"
                                                           :file-id="-1"
                                                           :feedback="{}"
                                                           :start-line="0"
                                                           :show-whitespace="true"
                                                           :warn-no-newline="false" />
                                    </div>
                                </b-tab>

                                <b-tab title="Input" class="row">
                                    <div class="col-6">
                                        <label>Input arguments:</label>
                                        <code class="form-control">{{ input.args }}</code>
                                    </div>

                                    <div class="col-6">
                                        <label>Input:</label>
                                        <inner-code-viewer class="rounded border"
                                                           :assignment="assignment"
                                                           :code-lines="prepareOutput(input.stdin)"
                                                           :file-id="-1"
                                                           :feedback="{}"
                                                           :start-line="0"
                                                           :show-whitespace="true"
                                                           :warn-no-newline="false" />
                                    </div>
                                </b-tab>

                                <b-tab title="Errors" class="row" v-if="ioSubStepProps(i, '', 'stderr')">
                                    <div class="col-12">
                                        <inner-code-viewer class="rounded border"
                                                           :assignment="assignment"
                                                           :code-lines="prepareOutput(ioSubStepProps(i, '', 'stderr'))"
                                                           :file-id="-1"
                                                           :feedback="{}"
                                                           :start-line="0"
                                                           :show-whitespace="true"
                                                           :warn-no-newline="false" />
                                    </div>
                                </b-tab>
                            </b-tabs>

                            <b-input-group class="mr-1 px-3 pb-3" prepend="Options">
                                <b-form-checkbox-group
                                    class="form-control"
                                    :options="ioOptions"
                                    :checked="input.options"
                                    @click.native.capture.prevent.stop/>
                            </b-input-group>
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

import { visualizeWhitespace } from '@/utils/visualize';

import Collapse from './Collapse';
import SubmitButton from './SubmitButton';
import DescriptionPopover from './DescriptionPopover';
import AutoTestState from './AutoTestState';
import InnerCodeViewer from './InnerCodeViewer';

export default {
    name: 'auto-test-step',

    props: {
        assignment: {
            type: Object,
            required: true,
        },

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
        const id = this.$utils.getUniqueId();

        return {
            id,
            stepCollapsed: true,
            collapseState: {},
            autoTestStepModalId: `auto-test-step-modal-${id}`,
        };
    },

    watch: {
        value() {
            console.log(this.value);
        },

        editable() {
            this.collapseState = {};
        },
    },

    computed: {
        valueCopy() {
            return this.$utils.deepCopy(this.value);
        },

        permissions() {
            return this.$utils.getProps(this, {}, 'assignment', 'course', 'permissions');
        },

        stepType() {
            const type = this.value.type;
            return this.testTypes.find(t => t.name === type);
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
            return this.$utils.getProps(this, [], 'value', 'data', 'inputs');
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
            return this.$utils.getProps(this, null, 'result', 'stepResults', this.value.id);
        },

        achievedPoints() {
            let points = this.$utils.getProps(this, '-', 'stepResult', 'achieved_points');
            if (typeof points === 'number' || points instanceof Number) {
                points = this.$utils.toMaxNDecimals(points, 2);
            }
            return points;
        },

        canViewDetails() {
            return (
                this.permissions.can_view_autotest_step_details &&
                (!this.value.hidden || this.permissions.can_view_hidden_autotest_steps)
            );
        },

        canViewOutput() {
            if (
                !this.result ||
                !this.canViewDetails ||
                (this.assignment.state !== 'done' &&
                    !this.permissions.can_view_autotest_before_done)
            ) {
                return false;
            }

            if (this.value.type === 'io_test') {
                return Array(this.value.data.inputs.length).every(
                    i => this.canViewSubStepOutput(i),
                );
            } else {
                return this.$utils.getProps(this, false, 'stepResult', 'finished');
            }
        },

        stepStdout() {
            const stdout = this.$utils.getProps(this, '', 'stepResult', 'log', 'stdout');
            return this.prepareOutput(stdout);
        },

        stepStderr() {
            const stderr = this.$utils.getProps(this, '', 'stepResult', 'log', 'stderr');
            return this.prepareOutput(stderr);
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
            const options = this.inputs[this.inputs.length - 1].options;

            return {
                name: '',
                args: '',
                stdin: '',
                output: '',
                weight: 1,
                options,
            };
        },

        addInput() {
            this.updateValue('inputs', [...this.inputs, this.createInput()]);
        },

        deleteInput(index) {
            this.updateValue('inputs', this.inputs.filter((_, i) => i !== index));
        },

        updateName(name) {
            this.$emit('input', Object.assign(this.valueCopy, { name }));
        },

        updateHidden(hidden) {
            this.$emit('input', Object.assign(this.valueCopy, { hidden, collapsed: true }));
        },

        updateCollapse(collapsed) {
            this.$emit('input', Object.assign(this.valueCopy, { collapsed }));
        },

        updateValue(key, value) {
            const copy = this.valueCopy;

            if (key === 'weight') {
                copy.weight = Number(value);
                this.$emit('input', copy);
                return;
            }

            let weight = Number(this.value.weight);
            if (key === 'inputs') {
                weight = (value || []).reduce((res, cur) => res + Number(cur.weight), 0);
                (value || []).forEach(cur => {
                    if (typeof cur.weight !== 'number' || !(cur.weight instanceof Number)) {
                        cur.weight = Number(cur.weight);
                    }
                });
            } else if (key === 'min_points') {
                // eslint-disable-next-line
                value = Number(value);
            }

            copy.data = {
                ...this.value.data,
                [key]: value,
            };
            copy.weight = weight;
            this.$emit('input', copy);
        },

        ioSubStepProps(i, defaultValue, ...props) {
            return this.$utils.getProps(this.stepResult, defaultValue, 'log', 'steps', i, ...props);
        },

        canViewSubStepOutput(i) {
            if (
                !this.result ||
                !this.canViewDetails ||
                (this.assignment.state !== 'done' &&
                    !this.permissions.can_view_autotest_before_done)
            ) {
                return false;
            }

            return (
                ['passed', 'failed', 'timed_out'].indexOf(
                    this.ioSubStepProps(i, false, 'state'),
                ) !== -1
            );
        },

        prepareOutput(output) {
            const lines = output ? output.split('\n') : ['No output.'];
            return lines.map(this.$utils.htmlEscape).map(visualizeWhitespace);
        },
    },

    components: {
        Icon,
        Collapse,
        SubmitButton,
        DescriptionPopover,
        AutoTestState,
        InnerCodeViewer,
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
    .step-type {
        height: 100%;
        width: auto;
        color: rgba(0, 0, 0, 0.5);
        border: 1px solid rgba(0, 0, 0, 0.125);
    }

    .name-input {
        flex: 1 1 18rem;
    }

    .points-input {
        flex: 0 1 12rem;
    }
}

.collapse-toggle {
    cursor: pointer;

    .fa-icon {
        transition: transform 250ms linear;
    }

    .x-collapsing .handle .fa-icon,
    .x-collapsed .handle .fa-icon,
    &.collapsed .fa-icon {
        transform: rotate(-90deg);
    }
}

.footer-wrapper {
    flex-direction: row;
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

    .step-summary {
        &.with-output:hover {
            background-color: rgba(0, 0, 0, 0.03);
            cursor: pointer;
        }

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

    td.shrink {
        width: 1px;
        white-space: nowrap;
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

    .card {
        border: 0;
    }

    code.form-control,
    pre.form-control {
        min-height: 5rem;
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

.io-input-options-wrapper {
    pointer-events: none;
}
</style>

<style lang="less">
.auto-test-step {
    .results-log-collapse-row {
        .card-header {
            background-color: inherit;
            border-bottom: 0;
        }

        .tab-pane {
            display: flex;
            padding: 0.75rem 0 0;
        }
    }

    .io-input-options-wrapper .custom-checkbox {
        margin-right: 0.5rem;
    }
}
</style>
