<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="rubric-viewer-row normal"
     :class="{ editable, locked }"
     @mouseenter="lockPopoverVisible = true"
     @mouseleave="lockPopoverVisible = false">
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

    <div class="rubric-row-items position-relative d-flex flex-row">
        <div v-for="item, i in rowItems"
             class="rubric-item pt-2 pl-2"
             :class="{
                 selected: item.id === selectedId,
                 'border-left': i > 0,
                 'pb-4': showProgressMeter,
             }"
             :style="{ flex: `0 0 ${100 / rowItems.length}%` }"
             @click="toggleItem(item)">
            <b class="mb-2">
                {{ item.points }} - {{ item.header }}

                <icon v-if="item.id === selectedId"
                      name="check"
                      class="float-right mr-2" />
            </b>

            <p class="description mb-0 pb-2 pr-2 text-justify text-wrap-pre">{{ item.description }}</p>
        </div>

        <div class="progress-meter"
             :style="{
                 opacity: showProgressMeter ? 1 : 0,
                 width: `${autoTestProgress}%`,
             }">
            <small :class="`progress-${readableAutoTestProgress}`">
                {{ readableAutoTestProgress }}%
            </small>
        </div>
    </div>
</div>
</template>

<script>
import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/lock';
import 'vue-awesome/icons/check';

import { AutoTestResult, RubricRow, RubricResult } from '@/models';

export default {
    name: 'rubric-viewer-normal-row',

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
        };
    },

    computed: {
        rowItems() {
            return this.rubricRow.items;
        },

        selectedItem() {
            return this.value.selected[this.rubricRow.id];
        },

        selectedId() {
            return this.$utils.getProps(this.selectedItem, null, 'id');
        },

        locked() {
            return this.rubricRow.locked;
        },

        showProgressMeter() {
            return this.locked === 'auto_test' && this.autoTestProgress != null;
        },

        lockPopover() {
            return this.rubricRow.lockMessage(this.autoTest, this.autoTestResult, this.value);
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

        readableAutoTestProgress() {
            const progress = this.autoTestProgress;
            return progress == null ? 0 : progress.toFixed(0);
        },
    },

    methods: {
        toggleItem(item) {
            if (!this.editable || this.locked) {
                return;
            }

            const rowId = this.rubricRow.id;
            const value = this.value.toggleItem(rowId, item);
            this.$emit('input', value);
        },
    },

    components: {
        Icon,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.rubric-item {
    line-height: 1.3;

    .rubric-viewer.editable .rubric-viewer-row.normal:not(.locked) & {
        cursor: pointer;

        &:hover {
            background-color: rgba(0, 0, 0, 0.125);
        }
    }

    &.selected {
        background-color: rgba(0, 0, 0, 0.09375);
    }

    .description {
        max-height: 5rem;
        overflow: auto;
    }
}
</style>
