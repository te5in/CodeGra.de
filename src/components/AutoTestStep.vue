<template>
<div class="auto-test-step"
     v-if="editable">
    <b-card no-body>
        <div class="step-header">
            <div v-b-toggle="collapseId"
                 class="collapse-toggle header-item"
                 :class="value.opened ? 'collapse-open' : ''">
                <icon name="chevron-down"/>
            </div>
            <div class="step-type header-item"
                 :style="{ 'background-color': stepType.color }">
                {{ stepType.name }}
            </div>
            <b-input-group prepend="Name"
                           class="name-input header-item"
                           v-if="!stepType.metaTest">
                <input class="form-control"
                       ref="nameInput"
                       :value="value.name"
                       @input="updateValue('name', $event.target.value)"/>
            </b-input-group>
            <b-input-group prepend="Weight"
                           class="points-input header-item"
                           v-b-popover.top.hover="weightPopoverText"
                           v-if="!stepType.metaTest">
                <input class="form-control"
                       type="number"
                       :disabled="stepType.value === 'io_test'"
                       :value="value.weight"
                       @input="updateValue('weight', $event.target.value)"/>
            </b-input-group>

            <div v-if="stepType.metaTest"
                 class="flex-padding-element"/>

            <submit-button
                :disabled="disableDelete"
                class="delete-btn header-item"
                :submit="() => {}"
                :wait-at-least="0"
                v-b-popover.top.hover="'Delete this step'"
                @after-success="$emit('delete')"
                confirm="Are you sure you want to delete this step?"
                variant="danger">
                <icon name="times"/>
            </submit-button>
        </div>

        <b-collapse :visible="value.opened"
                    @input="updateValue('opened', $event)"
                    :id="collapseId"
                    v-if="!value.metatest">
            <div class="io-test-wrapper card-body">
                <template v-if="!stepType.metaTest">
                    <label :for="programNameId">
                        Program to test
                    </label>
                    <input class="form-control"
                           :value="value.program"
                           :id="programNameId"
                           @input="updateValue('program', $event.target.value)"/>
                </template>
                <template v-else-if="stepType.value === 'check_points'">
                    <label>
                        Stop test suite if amount of points is below
                    </label>
                    <input class="form-control min-points-input"
                           type="number"
                           :value="value.minPoints"
                           @input="updateValue('minPoints', $event.target.value)"/>
                </template>

                <template v-if="stepType.value === 'custom_output'">
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
                    <input :value="value.regex"
                           :id="regexId"
                           class="form-control"
                           @input="updateValue('regex', $event.target.value)">
                </template>
                <template v-else-if="stepType.value === 'io_test'">
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
                                                       :id="optionsId(index)"
                                                       class="io-options"
                                                       @input="updateInput(index, 'options', $event)">
                                    <b-form-checkbox v-for="option in ioOptions"
                                                     :key="option.value"
                                                     :value="option.value">
                                        {{ option.text }}
                                    </b-form-checkbox>
                                </b-form-checkbox-group>
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
                                   :disabled="value.inputs.length < 2">
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
<tbody v-else-if="value.type === 'check_points'">
    <tr>
        <td>{{ index }}</td>
        <td colspan="2">Stop when you got less than {{ value.minPoints }} points.</td>
    </tr>
</tbody>
<tbody v-else-if="value.type === 'run_program'">
    <tr>
        <td>{{ index }}</td>
        <td>{{ value.name }}: Run <code>{{ value.program }}</code> and check for successful completion.</td>
        <td>{{ value.weight }}</td>
    </tr>
</tbody>
<tbody v-else-if="value.type === 'custom_output'">
    <tr>
        <td>{{ index }}</td>
        <td>{{ value.name }}: Run <code>{{ value.program }}</code> and parse its output.</td>
        <td>{{ value.weight }}</td>
    </tr>
</tbody>
<tbody v-else-if="value.type === 'io_test'">
    <tr>
        <td><b>{{ index }}</b></td>
        <td><b>{{ value.name }}</b></td>
        <td><b>{{ value.weight }}</b></td>
    </tr>
    <tr v-for="input, i in inputs"
        :key="i">
        <td>{{ index }}.{{ i + 1}}</td>
        <td>{{ input.name }}</td>
        <td>{{ input.weight }}</td>
    </tr>
</tbody>
</template>

<script>
import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/times';
import 'vue-awesome/icons/files-o';
import 'vue-awesome/icons/plus';
import 'vue-awesome/icons/caret-down';
import 'vue-awesome/icons/chevron-down';

import { getUniqueId } from '@/utils';

import SubmitButton from './SubmitButton';
import DescriptionPopover from './DescriptionPopover';

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

        stepTypes: {
            type: Array,
            required: true,
        },

        disableDelete: {
            type: Boolean,
            default: false,
        },
    },

    data() {
        return {
            id: getUniqueId(),
            arr: [],
            collapseState: {},
            mainCollapseState: this.collapseOpen,
        };
    },

    watch: {
        editable() {
            this.collapseState = {};
        },
    },

    computed: {
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

        stepType() {
            return this.stepTypes.find(t => t.value === this.value.type);
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
            return this.value.inputs || [];
        },

        weightPopoverText() {
            if (this.stepType.value === 'io_test') {
                return 'This is equal to the sum of the weights of each input.';
            } else {
                return '';
            }
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

        updateValue(key, value) {
            if (key === 'weight') {
                this.$emit('input', {
                    ...this.value,
                    weight: value,
                });
                return;
            }

            let weight = this.value.weight;
            if (key === 'inputs') {
                weight = (value || []).reduce(
                    (res, cur) => res + Number(cur.weight),
                    0,
                );
                if (Number.isNaN(weight)) {
                    weight = '-';
                }
            }

            this.$emit('input', {
                ...this.value,
                [key]: value,
                weight,
            });
        },
    },

    components: {
        Icon,
        SubmitButton,
        DescriptionPopover,
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

    .step-type {
        padding: 0.375rem 1rem;
        flex: 0 1 auto;
        color: @text-color-muted;
        border: 1px solid rgba(0, 0, 0, 0.125);
        border-radius: 0.25rem;
    }

    .name-input {
        border-radius: 0;
        flex: 1 1 20rem;
    }

    .points-input {
        flex: 0 1 12rem;
        .input-group-text, .form-control
        {
            border-left: 1px solid rgba(0, 0, 0, 0.125);
        }
    }

    .cur-prog-title {
        flex: 1;
        background: @footer-color;
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

.delete-btn {
    margin-left: 0 !important;
    float: right;
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
</style>
