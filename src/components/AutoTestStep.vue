<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<b-card v-if="editable" class="auto-test-step" no-body>
    <collapse :disabled="!canViewDetails"
              :speed="500"
              :collapsed="value.collapsed"
              @change="updateCollapse" >
        <b-card-header slot="handle" class="step-header p-1 d-flex align-items-center">
            <icon v-if="canViewDetails" :key="index" class="toggle mx-3" name="chevron-down" :scale="0.75" />
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
                           v-b-popover.top.hover="weightPopover"
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
                       @click.capture.stop="updateHidden(!value.hidden)"
                       v-b-popover.top.hover="hideStepPopover">
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

        <b-card-body v-if="canViewDetails">
            <template v-if="!stepType.meta">
                <label :for="programNameId">
                    Program to test

                    <description-popover hug-text>
                        A bash command line to be executed.

                        <template v-if="value.type === 'io_test'">
                            Additional arguments may be defined per input case if needed, which
                            will be appended to this string.
                        </template>
                    </description-popover>
                </label>

                <input class="form-control"
                       :value="value.data.program"
                       :id="programNameId"
                       @input="updateValue('program', $event.target.value)"/>
            </template>

            <template v-else-if="value.type === 'check_points'">
                <label :for="pointsThresholdId">
                    Stop test category if percentage of points achieved is below
                </label>

                <b-input-group>
                    <input class="form-control text-left"
                           :id="pointsThresholdId"
                           type="number"
                           :value="value.data.min_points"
                           min="0"
                           max="100"
                           @input="updateValue('min_points', $event.target.value)"/>

                    <b-input-group-append is-text>
                        %
                    </b-input-group-append>
                </b-input-group>
            </template>

            <template v-if="value.type === 'custom_output'">
                <hr/>

                <label :for="regexId">
                    Regex to match a grade

                    <description-popover hug-text>
                        This regex will be applied line by line, starting from the <b>last</b> line.
                        The regex should be a <i>Python</i> regex and must contain at least one
                        capture group. The first capture group should capture a valid python float,
                        the default regex captures a single float.
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
                    <div class="row io-input-wrapper">
                        <div class="col-6">
                            <b-form-fieldset>
                                <label :for="inputNameId(index)">Name</label>

                                <input class="form-control"
                                       :id="inputNameId(index)"
                                       :value="input.name"
                                       @input="updateInput(index, 'name', $event.target.value)"/>
                            </b-form-fieldset>

                            <b-form-fieldset>
                                <label :for="argsId(index)">
                                    Input arguments

                                    <description-popover hug-text>
                                        Extra arguments appended to the "Program to test" option.
                                    </description-popover>
                                </label>

                                <input class="form-control"
                                       :id="argsId(index)"
                                       :value="input.args"
                                       @input="updateInput(index, 'args', $event.target.value)"/>
                            </b-form-fieldset>

                            <label :for="stdinId(index)">
                                Input

                                <description-popover hug-text>
                                    Input passed to the program via <code>stdin</code>.
                                </description-popover>
                            </label>

                            <textarea class="form-control"
                                      :value="input.stdin"
                                      :id="stdinId(index)"
                                      rows="4"
                                      @input="updateInput(index, 'stdin', $event.target.value)"/>
                        </div>
                        <div class="col-6">
                            <label :for="optionsId(index)">
                                Options
                            </label>

                            <div class="form-control mb-3">
                                <b-form-checkbox-group v-model="input.options"
                                                       @change="optionToggled(index, $event)">
                                    <b-form-checkbox v-for="opt in ioOptions"
                                                     :key="opt.value"
                                                     class="d-block"
                                                     :value="opt.value"
                                                     :disabled="disabledOptions[index][opt.value]">
                                        {{ opt.text }}

                                        <description-popover hug-text>
                                            {{ opt.description }}
                                        </description-popover>
                                    </b-form-checkbox>
                                </b-form-checkbox-group>
                            </div>

                            <label :for="stdoutId(index)">
                                Expected output

                                <description-popover hug-text>
                                    Text to match the output of the program with, according to the
                                    rules selected above.
                                </description-popover>
                            </label>

                            <textarea class="form-control"
                                      :value="input.output"
                                      rows="4"
                                      :id="stdoutId(index)"
                                      @input="updateInput(index, 'output', $event.target.value)"/>
                        </div>
                    </div>

                    <div class="mt-3 mb-2 d-flex flex-row justify-content-between">
                        <div v-b-toggle="collapseAdvancedId(index)"
                             class="collapse-toggle align-self-center text-muted font-italic">
                            <icon name="caret-down" class="mr-2" />
                            Advanced options
                        </div>

                        <b-btn variant="danger"
                               v-b-popover.top.hover="'Delete this input and output case.'"
                               @click.capture.stop="deleteInput(index)"
                               :disabled="value.data.inputs.length < 2">
                            <icon name="times"/> Delete
                        </b-btn>
                    </div>

                    <b-collapse :id="collapseAdvancedId(index)"
                                class="advanced-collapse"
                                v-model="collapseState[index]">
                        <div class="p-3 border rounded">
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

                <b-button-toolbar class="justify-content-end">
                    <b-btn @click="addInput"
                           v-b-popover.top.hover="'Add another input and output case.'">
                        <icon name="plus"/> Input
                    </b-btn>
                </b-button-toolbar>
            </template>
        </b-card-body>
    </collapse>
</b-card>

<!-- Not editable -->
<tbody v-else class="auto-test-step">
    <template v-if="value.type === 'check_points'">
        <tr class="step-summary"
            :class="{ 'with-output': canViewOutput }"
            :key="resultsCollapseId"
            v-b-toggle="resultsCollapseId">
            <td class="expand shrink">
                <icon v-if="canViewOutput" name="chevron-down" :scale="0.75" />
                <icon v-else-if="value.hidden" name="eye-slash" :scale="0.85"
                      v-b-popover.hover.top="hiddenPopover" />
            </td>
            <td class="shrink">{{ index }}</td>
            <td colspan="2">
                <b>{{ stepName }}</b>

                <template v-if="canViewDetails">
                    Stop when you achieve less than
                    <code>{{ value.data.min_points }}%</code>
                    of the points possible.
                </template>
            </td>
            <td class="shrink text-center" v-if="result">
                <auto-test-state :result="stepResult" />
            </td>
        </tr>

        <tr v-if="canViewOutput" class="results-log-collapse-row">
            <td colspan="5">
                <b-collapse :id="resultsCollapseId" class="container-fluid">
                    <div class="row mb-3">
                        <div class="col-12">
                            You {{ stepResult.state === 'passed' ? 'scored' : 'did not score' }}
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
            <td class="expand shrink">
                <icon v-if="canViewOutput" name="chevron-down" :scale="0.75" />
                <icon v-else-if="value.hidden" name="eye-slash" :scale="0.85"
                        v-b-popover.hover.top="hiddenPopover" />
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
                        <b-tabs card no-fade>
                            <b-tab title="Output" class="mb-3 flex-wrap">
                                <p class="col-12 mb-1">
                                    <label>Exit code</label>
                                    <code>{{ $utils.getProps(stepResult.log, '(unknown)', 'exit_code') }}</code>
                                </p>

                                <div class="col-12">
                                    <label>Output</label>
                                    <inner-code-viewer class="rounded border"
                                                       :assignment="assignment"
                                                       :code-lines="stepStdout"
                                                       :file-id="-1"
                                                       :feedback="{}"
                                                       :start-line="0"
                                                       :show-whitespace="true"
                                                       :warn-no-newline="false"
                                                       :empty-file-message="'No output.'" />
                                </div>
                            </b-tab>

                            <b-tab title="Errors" class="mb-3" v-if="$utils.getProps(stepResult, null, 'log', 'stderr')">
                                <div class="col-12">
                                    <inner-code-viewer class="rounded border"
                                                       :assignment="assignment"
                                                       :code-lines="stepStderr"
                                                       :file-id="-1"
                                                       :feedback="{}"
                                                       :start-line="0"
                                                       :show-whitespace="true"
                                                       :warn-no-newline="false"
                                                       :empty-file-message="'No output.'" />
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
            :class="{ 'with-output': canViewDetails }"
            :key="resultsCollapseId"
            v-b-toggle="resultsCollapseId">
            <td class="expand shrink">
                <icon v-if="canViewDetails" name="chevron-down" :scale="0.75" />
                <icon v-else-if="value.hidden" name="eye-slash" :scale="0.85"
                        v-b-popover.hover.top="hiddenPopover" />
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

        <tr v-if="canViewDetails" class="results-log-collapse-row">
            <td colspan="5">
                <b-collapse :id="resultsCollapseId">
                    <b-card no-body v-if="canViewOutput">
                        <b-tabs card no-fade>
                            <b-tab title="Output" class="mb-3 flex-wrap">
                                <p class="col-6 mb-1" v-if="canViewDetails">
                                    <label>
                                        Match output on

                                        <description-popover hug-text>
                                            Search the output of the command for this regex. If it
                                            is found, the matched number of points is used as the
                                            score for this step.
                                        </description-popover>
                                    </label>

                                    <code>{{ value.data.regex }}</code>
                                </p>

                                <p class="col-6 mb-1" v-if="canViewDetails">
                                    <label>Exit code</label>
                                    <code>{{ $utils.getProps(stepResult.log, '(unknown)', 'exit_code') }}</code>
                                </p>

                                <div class="col-12">
                                    <label>Output</label>
                                    <inner-code-viewer class="rounded border"
                                                       :assignment="assignment"
                                                       :code-lines="stepStdout"
                                                       :file-id="-1"
                                                       :feedback="{}"
                                                       :start-line="0"
                                                       :show-whitespace="true"
                                                       :warn-no-newline="false"
                                                       :empty-file-message="'No output.'" />
                                </div>
                            </b-tab>

                            <b-tab title="Errors" class="mb-3" v-if="$utils.getProps(stepResult, null, 'log', 'stderr')">
                                <div class="col-12">
                                    <inner-code-viewer class="rounded border"
                                                       :assignment="assignment"
                                                       :code-lines="stepStderr"
                                                       :file-id="-1"
                                                       :feedback="{}"
                                                       :start-line="0"
                                                       :show-whitespace="true"
                                                       :warn-no-newline="false"
                                                       :empty-file-message="'No output.'" />
                                </div>
                            </b-tab>
                        </b-tabs>
                    </b-card>

                    <template v-else>
                        <p class="col-12 mb-3" v-if="canViewDetails">
                            <label>
                                Match output on

                                <description-popover hug-text>
                                    Search the output of the command for this regex. If it
                                    is found, the matched number of points is used as the
                                    score for this step.
                                </description-popover>
                            </label>

                            <code>{{ value.data.regex }}</code>
                        </p>
                    </template>
                </b-collapse>
            </td>
        </tr>
    </template>

    <template v-else-if="value.type === 'io_test'">
        <tr>
            <td class="expand shrink">
                <icon v-if="value.hidden" name="eye-slash" :scale="0.85"
                      v-b-popover.hover.top="hiddenPopover" />
            </td>
            <td class="shrink">{{ index }}</td>
            <td>
                <b>{{ stepName }}</b>

                <template v-if="canViewDetails && !result">
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
            <td class="shrink text-center" v-if="result">
                <auto-test-state v-if="stepResult.state === 'hidden'" :result="stepResult" />
            </td>
        </tr>

        <template v-for="input, i in inputs">
            <tr class="step-summary"
                :class="{ 'with-output': canViewDetails }"
                :key="`${resultsCollapseId}-${i}`"
                v-b-toggle="`${resultsCollapseId}-${i}`">
                <td class="expand shrink">
                    <icon v-if="canViewDetails" name="chevron-down" :scale="0.75" />
                </td>
                <td class="shrink">{{ index }}.{{ i + 1 }}</td>
                <td>
                    <template v-if="canViewDetails && result">
                        <b>{{ input.name }}</b>

                        Run <code>{{ value.data.program }} {{ input.args }}</code>
                        and match its output to an expected value.
                    </template>
                    <template v-else>
                        {{ input.name }}
                    </template>
                </td>
                <td class="shrink text-center">
                    <template v-if="result">
                        {{ ioSubStepProps(i, '-', 'achieved_points') }} /
                    </template>
                    {{ $utils.toMaxNDecimals(input.weight, 2) }}
                </td>
                <td class="shrink text-center" v-if="result">
                    <auto-test-state :result="ioSubStepProps(i, stepResult)" />
                </td>
            </tr>

            <tr v-if="canViewDetails" class="results-log-collapse-row">
                <td colspan="5">
                    <b-collapse :id="`${resultsCollapseId}-${i}`">
                        <b-card no-body v-if="canViewSubStepOutput(i)">
                            <b-tabs card no-fade>
                                <b-tab title="Output" class="mb-3 flex-wrap">
                                    <p v-if="ioSubStepProps(i, '', 'exit_code')" class="col-12 mb-1">
                                        <label>Exit code</label>
                                        <code>{{ ioSubStepProps(i, '', 'exit_code') }}</code>
                                    </p>

                                    <div class="col-6">
                                        <label>
                                            Expected output

                                            <description-popover hug-text>
                                                Expected output. This is interpreted as a regular
                                                expression when the <code>regex</code> option below is set.
                                            </description-popover>
                                        </label>

                                        <inner-code-viewer class="rounded border"
                                                           :assignment="assignment"
                                                           :code-lines="prepareOutput(input.output)"
                                                           :file-id="-1"
                                                           :feedback="{}"
                                                           :start-line="0"
                                                           :warn-no-newline="false"
                                                           :show-whitespace="true"
                                                           :empty-file-message="'No output.'" />
                                    </div>

                                    <div class="col-6">
                                        <label>
                                            Actual output
                                        </label>

                                        <inner-code-viewer class="rounded border"
                                                           :assignment="assignment"
                                                           :code-lines="prepareOutput(ioSubStepProps(i, '', 'stdout'))"
                                                           :file-id="-1"
                                                           :feedback="{}"
                                                           :start-line="0"
                                                           :warn-no-newline="false"
                                                           :show-whitespace="true"
                                                           :empty-file-message="'No output.'" />
                                    </div>
                                </b-tab>

                                <b-tab title="Input" class="mb-3">
                                    <div class="col-6">
                                        <label>
                                            Command line

                                            <description-popover hug-text>
                                                A bash command line to be executed.
                                            </description-popover>
                                        </label>

                                        <inner-code-viewer class="rounded border"
                                                           :assignment="assignment"
                                                           :code-lines="prepareOutput(`${value.data.program} ${input.args}`)"
                                                           :file-id="-1"
                                                           :feedback="{}"
                                                           :start-line="0"
                                                           :warn-no-newline="false"
                                                           :show-whitespace="true"
                                                           :no-line-numbers="true"
                                                           :empty-file-message="'No arguments.'" />
                                    </div>

                                    <div class="col-6">
                                        <label>
                                            Input

                                            <description-popover hug-text>
                                                Input passed to the executed program via
                                                <code>stdin</code>.
                                            </description-popover>
                                        </label>

                                        <inner-code-viewer class="rounded border"
                                                           :assignment="assignment"
                                                           :code-lines="prepareOutput(input.stdin)"
                                                           :file-id="-1"
                                                           :feedback="{}"
                                                           :start-line="0"
                                                           :warn-no-newline="false"
                                                           :show-whitespace="true"
                                                           :empty-file-message="'No input.'" />
                                    </div>
                                </b-tab>

                                <b-tab title="Errors" class="mb-3" v-if="ioSubStepProps(i, '', 'stderr')">
                                    <div class="col-12">
                                        <inner-code-viewer class="rounded border"
                                                           :assignment="assignment"
                                                           :code-lines="prepareOutput(ioSubStepProps(i, '', 'stderr'))"
                                                           :file-id="-1"
                                                           :feedback="{}"
                                                           :start-line="0"
                                                           :show-whitespace="true"
                                                           :warn-no-newline="true"
                                                           :empty-file-message="'No output.'" />
                                    </div>
                                </b-tab>
                            </b-tabs>
                        </b-card>

                        <template v-else>
                            <div class="col-12 mb-3">
                                <label>
                                    Command line

                                    <description-popover hug-text>
                                        A bash command line to be executed.
                                    </description-popover>
                                </label>

                                <inner-code-viewer class="rounded border"
                                                   :assignment="assignment"
                                                   :code-lines="prepareOutput(`${value.data.program} ${input.args}`)"
                                                   :file-id="-1"
                                                   :feedback="{}"
                                                   :start-line="0"
                                                   :warn-no-newline="false"
                                                   :show-whitespace="true"
                                                   :no-line-numbers="true"
                                                   :empty-file-message="'No arguments.'" />
                            </div>

                            <div class="col-12 mb-3">
                                <label>
                                    Input

                                    <description-popover hug-text>
                                        Input passed to the executed program via
                                        <code>stdin</code>.
                                    </description-popover>
                                </label>

                                <inner-code-viewer class="rounded border"
                                                   :assignment="assignment"
                                                   :code-lines="prepareOutput(input.stdin)"
                                                   :file-id="-1"
                                                   :feedback="{}"
                                                   :start-line="0"
                                                   :warn-no-newline="false"
                                                   :show-whitespace="true"
                                                   :empty-file-message="'No input.'" />
                            </div>

                            <div class="col-12 mb-3">
                                <label>
                                    Expected output

                                    <description-popover hug-text>
                                        Expected output. This is interpreted as a regular
                                        expression when the <code>regex</code> option below is set.
                                    </description-popover>
                                </label>

                                <inner-code-viewer class="rounded border"
                                                   :assignment="assignment"
                                                   :code-lines="prepareOutput(input.output)"
                                                   :file-id="-1"
                                                   :feedback="{}"
                                                   :start-line="0"
                                                   :warn-no-newline="false"
                                                   :show-whitespace="true"
                                                   :empty-file-message="'No output.'" />
                            </div>
                        </template>

                        <b-input-group class="mr-1 px-3 pb-3" prepend="Options">
                            <b-form-checkbox-group class="form-control"
                                                   :checked="input.options">
                                <div v-for="opt in ioOptions" :key="opt.value">
                                    <b-form-checkbox :value="opt.value"
                                                     class="readably-disabled"
                                                     disabled
                                                     @click.native.capture.prevent.stop>
                                        {{ opt.text }}
                                    </b-form-checkbox>

                                    <description-popover hug-text>
                                        {{ opt.description }}
                                    </description-popover>
                                </div>
                            </b-form-checkbox-group>
                        </b-input-group>
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

import * as assignmentStates from '@/store/assignment-states';
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
        isContinuous: {
            type: Boolean,
            default: false,
        },
    },

    data() {
        const id = this.$utils.getUniqueId();

        return {
            id,
            collapseState: {},
            codeFontSize: 14,
        };
    },

    watch: {
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

        pointsThresholdId() {
            return `auto-test-step-point-threshold-${this.id}`;
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
            const caseOpt = {
                text: 'Case insensitive',
                value: 'case',
                description:
                    'Ignore differences in letter case. I.e. "A" and "a" are considered equal.',
            };
            const trailingWsOpt = {
                text: 'Ignore trailing whitespace',
                value: 'trailing_whitespace',
                description:
                    'Ignore differences in whitespace at the end of lines. I.e. "abc  " and "abc" are considered equal.',
            };
            const substringOpt = {
                text: 'Substring',
                value: 'substring',
                description:
                    'Require the expected output to appear somewhere in the actual output, but allow more text before or after it.',
            };
            const regexOpt = {
                text: 'Regex',
                value: 'regex',
                description:
                    'Interpret the expected output as a Python regular expression, and check if the actual output matches it. Setting this also implies "Substring".',
            };

            const allWhitespaceOpt = {
                text: 'Ignore all whitespace',
                value: 'all_whitespace',
                description:
                    'Ignore all differences in whitespace, even newlines. I.e. " a b cd " and "abc d" are considered equal.',
            };

            substringOpt.requiredBy = [regexOpt];
            regexOpt.requires = substringOpt;

            allWhitespaceOpt.disallows = regexOpt;
            allWhitespaceOpt.requires = trailingWsOpt;
            regexOpt.disallows = allWhitespaceOpt;
            trailingWsOpt.requiredBy = [allWhitespaceOpt];

            return [caseOpt, trailingWsOpt, allWhitespaceOpt, substringOpt, regexOpt];
        },

        inputs() {
            return this.$utils.getProps(this, [], 'value', 'data', 'inputs');
        },

        disabledOptions() {
            return this.inputs.map(input => {
                const opts = input.options;

                return opts.reduce((acc, val) => {
                    const opt = this.ioOptions.find(o => o.value === val);
                    this.$utils.getProps(opt, [], 'requiredBy').forEach(required => {
                        if (opts.indexOf(required.value) !== -1) {
                            acc[opt.value] = true;
                        }
                    });
                    if (opt.disallows && opts.indexOf(opt.value) !== -1) {
                        acc[opt.disallows.value] = true;
                    }
                    return acc;
                }, {});
            });
        },

        hideStepPopover() {
            if (this.valueCopy.hidden) {
                return 'Make the details of this step visible to students.';
            } else {
                return 'Disable this step for Continuous Feedback runs and hide the details from students.';
            }
        },

        weightPopover() {
            if (this.value.type === 'io_test') {
                return 'This is equal to the sum of the weights of each input.';
            } else if (this.stepType.meta) {
                return 'This step does not count towards the score and thus has no weight.';
            } else {
                return '';
            }
        },

        hiddenPopover() {
            if (!this.canViewDetails) {
                return "You do not have permission to view this step's details.";
            } else {
                return "Students cannot view this step's details.";
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
            const result = this.result && this.stepResult.state !== 'hidden';
            const canViewDetails = this.canViewDetails;
            const canViewFeedback =
                this.isContinuous ||
                this.assignment.state === assignmentStates.DONE ||
                this.permissions.can_view_autotest_before_done;

            if (!result || !canViewDetails || !canViewFeedback) {
                return false;
            }

            if (this.value.type === 'io_test') {
                return Array(this.value.data.inputs.length).every(i =>
                    this.canViewSubStepOutput(i),
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
            this.$emit('input', Object.assign(this.valueCopy, { hidden }));
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
            return (
                this.canViewOutput &&
                ['passed', 'failed', 'timed_out'].indexOf(
                    this.ioSubStepProps(i, false, 'state'),
                ) !== -1
            );
        },

        prepareOutput(output) {
            const lines = (output || '').split('\n');
            return lines.map(this.$utils.htmlEscape).map(visualizeWhitespace);
        },

        optionToggled(index, newValue) {
            newValue.forEach(val => {
                const opt = this.ioOptions.find(o => o.value === val);
                if (opt.requires && newValue.indexOf(opt.requires.value) === -1) {
                    newValue.push(opt.requires.value);
                }
                if (opt.disallows) {
                    const toRemove = newValue.indexOf(opt.disallows.value);
                    if (toRemove !== -1) {
                        newValue.splice(toRemove, 1);
                    }
                }
            });

            const oldValue = this.value.data.inputs[index].options;

            if (oldValue.some((x, i) => x !== newValue[i])) {
                this.valueCopy.data.inputs[index].options = newValue;
                this.$emit('input', this.$utils.deepCopy(this.valueCopy));
            }
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
    .col-6 {
        display: flex;
        flex-direction: column;
    }

    textarea.form-control {
        flex: 1 1 auto;
        min-height: 4.5rem;
    }
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
    p:last-child {
        margin-bottom: 0;
    }

    td {
        border-top: 0;
        padding: 0;
    }

    .col-6,
    .col-12 {
        display: flex;
        flex-direction: column;
    }

    .card {
        border: 0;
    }
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

        .tab-content {
            border-top: 1px solid rgba(0, 0, 0, 0.125);
        }

        .custom-checkbox {
            margin-right: 0.75rem;
            pointer-events: none;
        }
    }
}
</style>
