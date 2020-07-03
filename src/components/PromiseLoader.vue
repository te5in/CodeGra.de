<template>
<div class="promise-loader d-inline">
    <template v-if="error">
        <fa-icon :id="`${compId}-icon`"
                 name="times"
                 class="text-danger"/>
        <b-popover show
                   :target="`${compId}-icon`"
                   triggers=""
                   variant="danger">
            <fa-icon name="times"
                     class="hide-button"
                     @click.native.stop="hideError"/>
            {{ $utils.getErrorMessage(error) }}
        </b-popover>
    </template>
    <cg-loader :center="false"
               :scale="1"
               v-else-if="state === 'loading'" />
    <fa-icon name="check"
             class="text-success"
             v-else
             :style="{ opacity: state === 'success' ? 1 : 0}" />
</div>
</template>

<script lang="ts">
    import { Vue, Component, Prop, Watch } from 'vue-property-decorator';

@Component
export default class PromiseLoader extends Vue {
    @Prop({ required: true }) promise!: Promise<unknown> | null;

    @Prop({ default: 250 }) waitAtLeast!: number;

    @Prop({ default: 750 }) duration!: number;

    state: 'success' | Error | 'loading' | 'hidden' = 'loading';

    promiseIdx: number = 0;

    compId = `promise-loader-${this.$utils.getUniqueId()}`;

    get error(): Error | null {
        if (this.state instanceof Error) {
            return this.state;
        }
        return null;
    }

    @Watch('promise', { immediate: true })
    onPromiseChange() {
        this.promiseIdx++;
        this.state = 'loading';
        const savedIdx = this.promiseIdx;

        if (this.promise == null) {
            this.state = 'hidden';
            return;
        }

        const onCorrect = (cont: () => unknown) => {
            if (this.promiseIdx === savedIdx) {
                cont();
            }
        };

        this.$utils.waitAtLeast(this.waitAtLeast, this.promise).then(
            response => {
                onCorrect(() => {
                    this.state = 'success';
                    this.$emit('success', response);

                    setTimeout(() => {
                        onCorrect(() => {
                            this.state = 'hidden';
                            this.$emit('after-success', response);
                        });
                        this.state = 'hidden';
                    }, this.duration);
                });
            },
            err => {
                onCorrect(() => {
                    this.state = err;
                    this.$emit('error', err);
                });
            },
        );
    }

    hideError() {
        this.state = 'hidden';
        this.$emit('after-error');
    }
}
</script>

<style lang="less" scoped>
.fa-icon {
    width: 1rem;
}
</style>
