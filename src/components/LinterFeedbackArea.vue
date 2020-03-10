<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="linter-feedback-inner">
    <b-popover placement="top"
               triggers="hover"
               :target="divId">
        <table class="linter-feedback">
            <tr v-for="(val, i) in feedback"
                :key="i">
                <td class="pr-3">
                    <b>{{ val[0] }}</b>
                </td>
                <td class="text-left">
                    <template v-if="val[1].code">
                        [{{ val[1].code }}]
                    </template>
                    {{ val[1].msg }}
                </td>
            </tr>
        </table>
    </b-popover>
    <div :id="divId"
         class="linter-toggle"/>
</div>
</template>

<script>
let i = 0;

export default {
    name: 'linter-feedback-area',

    props: ['feedback'],

    data() {
        return {
            divId: `linterFeedback-${i++}`,
        };
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.linter-feedback-inner {
    display: inline;
}

.linter-toggle {
    min-width: @code-linum-width;
    height: 100%;
    top: 0;
    right: 100%;
    position: absolute;
}
</style>
