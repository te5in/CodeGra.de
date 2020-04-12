<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<multiselect :value="value"
             @select="onSelect"
             @remove="onRemove"
             :hide-selected="false"
             :options="students"
             :multiple="multiple"
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
<input :value="inputValue"
       @input="onInput($event.target.value)"
       class="user-selector form-control"
       :class="{ disabled, 'border': !noBorder }"
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
        multiple: {
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

        inputValue() {
            if (this.multiple) {
                return (this.value || []).map(x => x.username).join(', ');
            }
            return this.value ? '' : this.value.username;
        },
    },

    methods: {
        ...mapActions('users', ['addOrUpdateUser']),

        onSelect(newUser) {
            let toEmit = newUser;
            if (toEmit.username === this.myUsername) {
                toEmit.id = this.myId;
            }
            toEmit = this.getUserById(toEmit.id) || toEmit;

            if (this.multiple) {
                this.$emit('input', [...(this.value || []), toEmit]);
            } else {
                this.$emit('input', toEmit);
            }
        },

        onRemove(removedUser) {
            if (this.multiple) {
                this.$emit('input', (this.value || []).filter(user => user.id !== removedUser.id));
            } else {
                this.$emit('input', null);
            }
        },

        onInput(input) {
            const byUsername = username => {
                let res = null;
                if (username === this.myUsername) {
                    res = this.getUserById(this.myId);
                }
                return res || { username };
            };

            let toEmit;
            if (this.multiple) {
                toEmit = input.split(/,\s+/).map(byUsername);
            } else {
                toEmit = byUsername(input);
            }

            this.$emit('input', toEmit);
        },

        queryMatches() {
            if (this.searchQuery == null || this.value == null) {
                return false;
            }

            if (this.searchQuery.length === 0) {
                return true;
            }

            const arr = this.$utils.ensureArray(this.value);
            if (arr.length === 0 || arr[arr.lenght - 1] == null) {
                return false;
            }
            const value = arr[arr.length - 1];
            const username = value.username.toLocaleLowerCase();
            const name = value.name ? value.name.toLocaleLowerCase() : ';';

            return this.searchQuery.split(' ').every(queryWord => {
                const word = queryWord.toLocaleLowerCase();
                return username.indexOf(word) >= 0 || name.indexOf(word) >= 0;
            });
        },

        asyncFind(query) {
            this.stopLoadingStudents();
            this.searchQuery = query;

            if (this.queryTooSmall && !this.multiple && this.value && this.queryMatches()) {
                this.students = this.$utils.ensureArray(this.value);
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
                        async ({ data }) => {
                            if (stop) {
                                return;
                            }

                            await Promise.all(data.map(user => this.addOrUpdateUser({ user })));
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

    @{dark-mode} {
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
