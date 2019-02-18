<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<multiselect :value="value"
             @input="onInput"
             :hide-selected="false"
             :options="students"
             :multiple="false"
             :searchable="true"
             :select-label="selectLabel"
             @search-change="asyncFind"
             :internal-search="true"
             :custom-label="o => `${o.name} (${o.username})`"
             :loading="loadingStudents"
             class="user-selector"
             style="flex: 1;"
             :placeholder="placeholder"
             :disabled="disabled"
             label="name"
             track-by="username"
             :class="{ disabled }"
             v-if="useSelector">
    <span class="caret" slot="caret"><icon name="search"/></span>
    <span slot="noResult" v-if="queryTooSmall" class="text-muted">
        Please give a search string with at least 3 non-whitespace characters.
    </span>
    <span slot="noResult" v-else class="text-muted">
        No results were found. You can search on name and username.
    </span>
</multiselect>
<input :value="value ? value.username : ''"
       @input="onInput({ username: $event.target.value })"
       class="form-control user-selector"
       :class="{ disabled }"
       :placeholder="placeholder"
       :disabled="disabled"
       v-else/>
</template>

<script>
import Multiselect from 'vue-multiselect';

import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/search';

export default {
    name: 'user-selector',

    props: {
        disabled: {
            type: Boolean,
            default: false,
        },
        placeholder: {
            type: String,
            required: true,
        },

        useSelector: {
            type: Boolean,
            default: true,
        },

        filterStudents: {
            type: Function,
            default: () => true,
        },

        selectLabel: {
            type: String,
            default: 'Press enter to select',
        },

        value: {
            required: true,
        },

        extraParams: {
            type: Object,
            default: () => {},
        },

        baseUrl: {
            type: String,
            default: '/api/v1/users/',
        },
    },

    data() {
        return {
            students: [],
            username: '',
            loadingStudents: false,
            stopLoadingStudents: () => {},
            searchQuery: null,
        };
    },

    watch: {
        value() {
            if (!this.value) {
                this.students = [];
            }
        },
    },

    computed: {
        queryTooSmall() {
            return !this.searchQuery || this.searchQuery.replace(/\s/g, '').length < 3;
        },
    },

    methods: {
        onInput(newValue) {
            this.$emit('input', newValue);
        },

        queryMatches() {
            if (this.searchQuery == null || this.value == null) {
                return false;
            }

            if (this.searchQuery.length === 0) {
                return true;
            }

            const username = this.value.username.toLocaleLowerCase();
            const name = this.value.name ? this.value.name.toLocaleLowerCase() : ';';

            return this.searchQuery.split(' ').every(queryWord => {
                const word = queryWord.toLocaleLowerCase();
                return username.indexOf(word) >= 0 || name.indexOf(word) >= 0;
            });
        },

        asyncFind(query) {
            this.stopLoadingStudents();
            this.searchQuery = query;

            if (this.queryTooSmall && this.value && this.queryMatches()) {
                this.students = [this.value];
                this.loadingStudents = false;
            } else if (this.queryTooSmall) {
                this.students = [];
                this.loadingStudents = false;
            } else {
                this.loadingStudents = true;
                let stop = false;
                let id;
                const params = Object.assign({ q: query }, this.extraParams);
                id = setTimeout(() => {
                    this.$http.get(this.baseUrl, { params }).then(
                        ({ data }) => {
                            if (stop) {
                                return;
                            }

                            this.loadingStudentsCallback = null;
                            this.students = data.filter(this.filterStudents);
                            this.loadingStudents = false;
                        },
                        err => {
                            if (stop) {
                                return;
                            }

                            if (err.response.data.code === 'RATE_LIMIT_EXCEEDED') {
                                id = setTimeout(() => this.asyncFind(query), 1000);
                            } else {
                                throw err;
                            }
                        },
                    );
                }, 250);

                this.stopLoadingStudents = () => {
                    clearTimeout(id);
                    stop = true;
                };
            }
        },
    },

    components: {
        Multiselect,
        Icon,
    },
};
</script>

<style lang="less" scoped>
.disabled {
    cursor: not-allowed;
}

.caret {
    line-height: 16px;
    display: block;
    position: absolute;
    box-sizing: border-box;
    width: 40px;
    height: 38px;
    right: 1px;
    top: 13px;
    margin: 0;
    text-decoration: none;
    text-align: center;
    cursor: pointer;
}
</style>

<style lang="less">
@import '~mixins.less';

.user-selector.multiselect {
    &.disabled,
    &.disabled > .multiselect__select {
        cursor: not-allowed !important;
        pointer-events: initial;
    }

    .multiselect__tags {
        border-top-right-radius: 0;
        border-bottom-right-radius: 0;
    }

    .multiselect__option {
        white-space: normal;
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
}
</style>
