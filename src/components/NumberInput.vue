<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<input :value="value"
       @input="emitFromEvent"
       @keydown.down="decValue"
       @keydown.up="incValue"
       class="number-input form-control"
       type="tel"/>
</template>

<script lang="ts">
import { Vue, Component, Prop } from 'vue-property-decorator';

@Component
export default class NumberInput extends Vue {
    @Prop({
        type: [Number, Object],
        validator: x => {
            if (x instanceof Object) {
                return x === null;
            } else {
                return true;
            }
        },
        default: null,
    })
    value!: number | null;

    // The <input>'s "type" attribute _must_ be "number", so we have a prop named
    // "type" to prevent the <input>'s "type" attribute to be overridden, while
    // still allowing to set other <input> attributes on the component.
    @Prop({ type: String, default: 'tel' })
    type!: string;

    @Prop({ type: Number, default: 1 })
    step!: number;

    @Prop({ type: Number, default: -Infinity })
    min!: number;

    @Prop({ type: Number, default: Infinity })
    max!: number;

    // If the current value is a valid number, emit that number as a float.
    // Otherwise emit `null`.
    emitValue(value: string | number | null) {
        let v: number | null = this.$utils.parseOrKeepFloat(value);
        if (Number.isNaN(v)) {
            v = null;
        } else {
            v = Math.min(Math.max(this.min, v), this.max);
        }
        this.$emit('input', v);
    }

    emitFromEvent(event: InputEvent) {
        const el = event.target as HTMLInputElement;
        this.emitValue(el.value);
    }

    decValue() {
        this.maybeUpdate(v => v - this.step);
    }

    incValue() {
        this.maybeUpdate(v => v + this.step);
    }

    maybeUpdate(f: (v: number) => number) {
        const v = this.value;
        if (typeof v === 'number') {
            this.emitValue(f(v));
        } else {
            this.emitValue(null);
        }
    }
}
</script>

<style lang="less" scoped>
input {
    text-align: right;
}
</style>
