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
             :class="{ disabled, 'no-border': noBorder }"
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
       class="user-selector form-control border-left-0 border-bottom-0 border-right-0 rounded-top-0"
       :class="{ disabled, 'border-top': !noBorder }"
       :placeholder="placeholder"
       :disabled="disabled"
       v-else/>
</template>

<script>
import { mapGetters, mapActions } from 'vuex';
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
        noBorder: {
            type: Boolean,
            default: false,
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
        ...mapGetters('user', {
            myId: 'id',
            myUsername: 'username',
        }),
        ...mapGetters('users', { getUserById: 'getUser' }),

        queryTooSmall() {
            return !this.searchQuery || this.searchQuery.replace(/\s/g, '').length < 3;
        },
    },

    methods: {
        ...mapActions('users', ['addOrUpdateUser']),

        onInput(newValue) {
            if (newValue != null && newValue.username) {
                let toEmit = newValue;
                if (toEmit.username === this.myUsername) {
                    toEmit.id = this.myId;
                }
                toEmit = this.getUserById(toEmit.id) || toEmit;
                this.$emit('input', toEmit);
            } else {
                this.$emit('input', null);
            }
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

                            data.map(user => this.addOrUpdateUser({ user }));
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
@import '~mixins.less';

.disabled {
    cursor: not-allowed;
}

.caret {
    display: block;
    position: absolute;
    width: 40px;
    height: 100%;
    right: 0;
    cursor: pointer;

    #app.dark & {
        color: @text-color-dark;
    }

    .fa-icon {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
    }
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

    &.no-border .multiselect__tags {
        border-width: 0 !important;
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
            background: rgb(217, 83, 79) !important;

            &::after {
                background: rgb(217, 83, 79) !important;
            }
        }
    }
}
</style>
