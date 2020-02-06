<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="rubric-viewer-row continuous"
     :class="{ editable, locked }"
     @mouseenter="lockPopoverVisible = true"
     @mouseleave="lockPopoverVisible = false">
    <div class="rubric-row-header">
        <div class="row-description border-bottom">
            <template v-if="locked">
                <icon name="lock"
                      class="rubric-lock float-right mx-3 my-2"
                      :id="`rubric-lock-${id}`" />

                <!-- We need to key this popover to make sure it actually
                     changes when the content changes. -->
                <b-popover :show="lockPopoverVisible"
                           :target="`rubric-lock-${id}`"
                           :content="lockPopover"
                           :key="lockPopover"
                           triggers=""
                           placement="top"
                           boundary="window" />
            </template>

            <p class="text-wrap-pre mb-0 py-2 px-3" v-if="rubricRow.description">{{ rubricRow.description }}</p>
            <p class="mb-0 py-2 px-3 text-muted font-italic" v-else>
                This category has no description.
            </p>
        </div>

        <div class="position-relative mb-0 pt-2 pb-3 px-4"
             :class="{ 'pb-4': showProgressMeter }">
            <b>0</b>
            <b class="float-right">{{ onlyItem.points }}</b>

            <div class="progress-meter"
                 :style="{
                     opacity: showProgressMeter ? 1 : 0,
                     width: `${progressWidth}%`,
                 }">
                <small class="text-center" :class="`progress-${readableMultiplier}`">
                    {{ $utils.toMaxNDecimals(onlyItem.points * multiplier / 100, 2) }}
                </small>
            </div>
        </div>
    </div>

    <b-input-group class="percentage-input"
                   append="%">
        <input class="percentage form-control border-bottom-0 border-left-0 rounded-left-0"
               type="number"
               step="1"
               min="0"
               max="100"
               placeholder="Percentage"
               :value="$utils.toMaxNDecimals(multiplier, 2)"
               :disabled="!editable || locked"
               @input="setMultiplier(timerDelay)"
               @keydown.ctrl.enter="submitResult"
               ref="multiplierInput" />
    </b-input-group>
</div>
</template>

<script>
import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/lock';
import 'vue-awesome/icons/check';

import { AutoTestResult, RubricRow, RubricResult } from '@/models';

export default {
    name: 'rubric-viewer-continuous-row',

    props: {
        value: {
            type: RubricResult,
            required: true,
        },
        rubricRow: {
            type: RubricRow,
            required: true,
        },
        assignment: {
            type: Object,
            required: true,
        },
        autoTest: {
            type: Object,
            default: null,
        },
        autoTestResult: {
            type: AutoTestResult,
            default: null,
        },
        editable: {
            type: Boolean,
            default: false,
        },
        active: {
            type: Boolean,
            default: false,
        },
    },

    data() {
        return {
            id: this.$utils.getUniqueId(),
            lockPopoverVisible: false,
            timerId: null,
            timerDelay: 75,
        };
    },

    computed: {
        onlyItem() {
            return this.rubricRow.items[0];
        },

        resultItem() {
            return this.$utils.getProps(this.value, null, 'selected', this.rubricRow.id);
        },

        multiplier() {
            const resultMult = this.$utils.getProps(this.resultItem, null, 'multiplier');

            if (typeof this.autoTestProgress === 'number') {
                return this.autoTestProgress;
            } else if (typeof resultMult === 'number') {
                return 100 * resultMult;
            } else {
                return null;
            }
        },

        autoTestProgress() {
            if (this.autoTestResult == null) {
                return null;
            }

            const state = this.$utils.getProps(this.autoTestResult, null, 'state');
            const percentage = this.$utils.getProps(
                this.autoTestResult,
                null,
                'rubricResults',
                this.rubricRow.id,
                'percentage',
            );

            return state === 'not_started' ? null : percentage;
        },

        readableMultiplier() {
            return this.$utils.toMaxNDecimals(this.multiplier, 0);
        },

        locked() {
            return this.rubricRow.locked;
        },

        showProgressMeter() {
            if (this.multiplier != null) {
                return this.multiplier >= 0 && this.multiplier <= 100;
            } else {
                return false;
            }
        },

        progressWidth() {
            if (this.multiplier == null) {
                return null;
            } else {
                return Math.max(0, Math.min(this.multiplier, 100));
            }
        },

        lockPopover() {
            return this.rubricRow.lockMessage(this.autoTest, this.autoTestResult, this.value);
        },
    },

    methods: {
        setMultiplier(delay = 0) {
            if (!this.editable || this.locked) {
                return;
            }

            clearTimeout(this.timerId);

            const inputEl = this.$refs.multiplierInput;
            const rowId = this.rubricRow.id;
            const item = this.onlyItem;

            let value = parseFloat(inputEl.value);
            if (!Number.isNaN(value)) {
                value /= 100;
            } else if (inputEl.validity.valid) {
                value = null;
            } else {
                return;
            }

            const newResult = this.value.setMultiplier(rowId, item, value);

            if (delay) {
                this.timerId = setTimeout(() => {
                    this.timerId = null;
                    this.$emit('input', newResult);
                }, this.timerDelay);
            } else {
                this.$emit('input', newResult);
            }
        },

        submitResult() {
            clearTimeout(this.timerId);
            this.setMultiplier(this.$refs.multiplierInput);
            this.$nextTick(() => {
                this.$emit('submit');
            });
        },
    },

    components: {
        Icon,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.rubric-viewer-row.continuous {
    overflow: hidden;
}

.rubric-item {
    line-height: 1.3;

    .rubric-viewer.editable .rubric-viewer-row.normal:not(.locked) & {
        cursor: pointer;

        &:hover {
            background-color: rgba(0, 0, 0, 0.0625);
        }
    }

    &.selected {
        background-color: rgba(0, 0, 0, 0.125) !important;
    }
}

input.percentage {
    background-color: white;
}
</style>

<style lang="less">
.rubric-viewer-row.continuous .percentage-input {
    .input-group-text {
        border-bottom: 0;
        border-right: 0;
        border-top-right-radius: 0;
    }
}
</style>
