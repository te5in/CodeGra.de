<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<loader v-if="loading"/>
<div class="pref-manager" v-else>
    <table class="table settings-table"
            style="margin-bottom: 0;">
        <tbody>
            <tr v-if="showWhitespace">
                <td>
                    Whitespace
                    <loader :scale="1" :center="true" v-if="whiteLoading"/>
                </td>
                <td>
                    <toggle v-model="whitespace" label-on="Show" label-off="Hide"/>
                </td>
            </tr>
            <tr v-if="showLanguage">
                <td>Language
                    <loader :scale="1" :center="true" v-if="langLoading"/>
                </td>
                <td>
                    <multiselect v-model="selectedLanguage"
                                    :hide-selected="selectedLanguage === 'Default'"
                                    deselect-label="Reset language"
                                    select-label="Select language"
                                    :options="languages"/>
                </td>
            </tr>
            <tr v-if="showFontSize">
                <td style="text-align: left;">
                    Code font size
                    <loader v-show="fontSizeLoading > 0" :scale="1" center/>
                </td>
                <td>
                    <b-input-group right="px">
                        <input :value="fontSize"
                                @input="fontSizeChanged($event.target.value)"
                                class="form-control"
                                type="number"
                                step="1"
                                min="1"/>
                    </b-input-group>
                </td>
            </tr>
            <tr v-if="showContextAmount">
                <td style="text-align: left;">
                    Amount of context
                    <loader v-show="contextAmountLoading > 0" :scale="1" center/>
                </td>
                <td>
                    <b-input-group right="px">
                        <input :value="contextAmount"
                                @input="contextAmountChanged($event.target.value)"
                                class="form-control"
                                type="number"
                                step="1"
                                min="0"/>
                    </b-input-group>
                </td>
            </tr>
            <tr v-if="showTheme">
                <td>Theme</td>
                <td>
                    <toggle :value="darkMode"
                            @input="setDarkMode"
                            label-on="Dark"
                            label-off="Light"/>
                </td>
            </tr>
        </tbody>
    </table>
</div>
</template>

<script>
import { listLanguages } from 'highlightjs';
import { mapActions, mapGetters } from 'vuex';
import Multiselect from 'vue-multiselect';

import { cmpNoCase, waitAtLeast } from '@/utils';

import Toggle from './Toggle';
import Loader from './Loader';

export default {
    name: 'preference-manager',

    components: {
        Toggle,
        Loader,
        Multiselect,
    },

    props: {
        showWhitespace: {
            type: Boolean,
            default: true,
        },
        showLanguage: {
            type: Boolean,
            default: true,
        },
        showFontSize: {
            type: Boolean,
            default: true,
        },
        showTheme: {
            type: Boolean,
            default: true,
        },
        fileId: {
            type: [Number, String],
            default: null,
        },

        showContextAmount: {
            default: false,
        },
    },

    data() {
        const languages = listLanguages();
        languages.push('plain');
        languages.sort(cmpNoCase);
        languages.unshift('Default');
        return {
            loading: true,
            languages,
            whitespace: true,
            contextAmountLoading: 0,
            fontSizeLoading: 0,
            langLoading: false,
            whiteLoading: false,
            selectedLanguage: -1,
        };
    },

    computed: {
        ...mapGetters('pref', ['fontSize', 'contextAmount', 'darkMode']),
    },

    methods: {
        ...mapActions('pref', ['setFontSize', 'setContextAmount', 'setDarkMode']),

        contextAmountChanged(val) {
            this.contextAmountLoading += 1;
            const contextAmount = Math.max(Number(val), 0);
            waitAtLeast(200, this.setContextAmount(contextAmount)).then(() => {
                this.contextAmountLoading -= 1;
                this.$emit('context-amount', contextAmount);
            });
        },

        fontSizeChanged(val) {
            this.fontSizeLoading += 1;
            const fontSize = Math.max(Number(val), 1);
            waitAtLeast(200, this.setFontSize(fontSize)).then(() => {
                this.fontSizeLoading -= 1;
                this.$emit('font-size', fontSize);
            });
        },

        loadValues() {
            this.loading = true;

            return Promise.all([this.loadWhitespace(), this.loadLanguage()]).then(() => {
                this.loading = false;
            });
        },

        loadWhitespace() {
            if (this.showWhitespace) {
                return this.$whitespaceStore.getItem(`${this.fileId}`).then(white => {
                    this.whitespace = white === null || white;
                });
            } else {
                return null;
            }
        },

        loadLanguage() {
            if (this.showLanguage) {
                return this.$hlanguageStore.getItem(`${this.fileId}`).then(lang => {
                    this.selectedLanguage = lang || 'Default';
                });
            } else {
                return null;
            }
        },
    },

    mounted() {
        this.loadValues();
    },

    watch: {
        showWhitespace(newVal) {
            if (newVal) {
                this.loadWhitespace();
            }
        },

        showLanguage(newVal) {
            if (newVal) {
                this.loadLanguage();
            }
        },

        fileId(newVal, oldVal) {
            if (newVal != null && newVal !== oldVal) {
                this.loadValues();
            }
        },

        selectedLanguage(lang, old) {
            if (old === -1) return;

            if (lang == null) {
                this.selectedLanguage = 'Default';
            } else {
                this.langLoading = true;
                this.$hlanguageStore.setItem(`${this.fileId}`, lang).then(() => {
                    this.langLoading = false;
                    this.$emit('language', lang);
                });
            }
        },

        whitespace(val) {
            this.whiteLoading = true;
            waitAtLeast(200, this.$whitespaceStore.setItem(`${this.fileId}`, val)).then(() => {
                this.whiteLoading = false;
                this.$emit('whitespace', val);
            });
        },
    },
};
</script>

<style lang="less">
@import '~mixins.less';

.pref-manager {
    #app.dark ~ .popover & .table {
        .dark-table-colors;
    }

    #app.dark ~ .popover & .table {
        .dark-input-colors;
    }

    #app.dark ~ .popover & .input-group {
        .dark-input-group-colors;
    }

    .table {
        .loader {
            margin-top: 4px;
            float: right;
        }
    }

    .multiselect__option--highlight {
        background: @color-primary;

        &::after {
            background: @color-primary;
        }

        &.multiselect__option--selected {
            background: #d9534f !important;

            &::after {
                background: #d9534f !important;
            }
        }
    }

    .table td {
        vertical-align: middle;
        text-align: left;

        &:first-child {
            width: 10em;
        }
    }
}
</style>
