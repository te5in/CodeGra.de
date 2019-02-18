<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<loader :scale="2" class="" v-if="loading"/>
<div class="snippet-manager" v-else>
    <b-form-group class="filter-group">
        <input v-model="filter"
               class="form-control"
               placeholder="Type to Search"
               v-on:keyup.enter="submit"/>
    </b-form-group>
    <b-table striped
             class="snippets-table"
             :items="allSnippets"
             :fields="fields"
             :filter="filter"
             response>

        <template slot="key" slot-scope="item">
            <b-form-group>
                <input type="text"
                       class="form-control"
                       placeholder="Key"
                       :value="item.item.key"
                       @input="snippetKeyChanged(item.item, $event.target.value)"
                       @keyup.ctrl.enter="clickSaveSnippet(item.index)"/>
            </b-form-group>
        </template>

        <template slot="text" slot-scope="item">
            <b-form-group>
                <input type="text"
                       class="form-control"
                       placeholder="Value"
                       :value="item.item.value"
                       @input="snippetValueChanged(item.item, $event.target.value)"
                       @keyup.ctrl.enter="clickSaveSnippet(item.index)"/>
            </b-form-group>
        </template>

        <template slot="actions" slot-scope="item">
            <b-button-group class="button-wrapper">
                <submit-button size="sm"
                               :variant="hasSnippetChanged(item.item) ? 'warning' : 'primary'"
                               :ref="`snippetSaveButton-${item.index}`"
                               :disabled="!canUpdateSnippet(item.item)"
                               :submit="() => saveSnippet(item.item)"
                               v-b-popover.top.hover="saveButtonPopover(item.item)">
                    <icon name="floppy-o"/>
                </submit-button>

                <b-btn v-if="hasSnippetChanged(item.item)"
                       size="sm"
                       variant="danger"
                       @click="resetSnippet(item.item)"
                       v-b-popover.top.hover="'Reset changes'">
                    <icon name="reply"/>
                </b-btn>

                <submit-button v-else-if="item.item.id != null || item.index < allSnippets.length - 1"
                               size="sm"
                               variant="danger"
                               confirm="Are you sure you want to delete this snippet?"
                               :submit="() => deleteSnippet(item.item)"
                               @after-success="afterDeleteSnippet(item.item, item.index)"
                               v-b-popover.top.hover="'Delete snippet'">
                    <icon name="times"/>
                </submit-button>
            </b-button-group>
        </template>
    </b-table>
</div>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';

import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/times';
import 'vue-awesome/icons/floppy-o';
import 'vue-awesome/icons/reply';

import { cmpNoCase } from '@/utils';

import Loader from './Loader';
import SubmitButton from './SubmitButton';

export default {
    name: 'snippet-manager',

    data() {
        return {
            loading: true,
            filter: null,
            newSnippets: [this.makeSnippet()],
            fields: [
                {
                    key: 'key',
                    label: 'Key',
                },
                {
                    key: 'text',
                    label: 'Text',
                },
                {
                    key: 'actions',
                    label: 'Actions',
                },
            ],
            errorMessages: {
                spacesInKey: 'No spaces allowed!',
                emptyKey: 'Snippet key cannot be empty',
                duplicateKey: 'Snippet key must be unique',
                emptyValue: 'Snippet value cannot be empty',
                unchangedSnippet: 'This snippet is unchanged.',
                unsavedChanges: 'This snippet has unsaved changes!',
            },
        };
    },

    computed: {
        ...mapGetters('user', ['snippets']),

        storedSnippets() {
            return Object.values(this.snippets)
                .map(snip =>
                    Object.assign({}, snip, {
                        origKey: snip.key,
                        origValue: snip.value,
                        keyError: '',
                        valueError: '',
                    }),
                )
                .sort((a, b) => cmpNoCase(a.key, b.key));
        },

        allSnippets() {
            return this.storedSnippets.concat(this.newSnippets);
        },
    },

    watch: {
        newSnippets(newSnippets) {
            const len = newSnippets.length;
            if (len === 0 || this.hasSnippetChanged(newSnippets[len - 1])) {
                newSnippets.push(this.makeSnippet());
            }
        },
    },

    methods: {
        ...mapActions({
            refreshSnippets: 'user/refreshSnippets',
            addSnippetToStore: 'user/addSnippet',
            updateSnippetInStore: 'user/updateSnippet',
            deleteSnippetFromStore: 'user/deleteSnippet',
        }),

        makeSnippet() {
            return {
                id: null,
                key: '',
                origKey: '',
                value: '',
                origValue: '',
                keyError: '',
                valueError: '',
            };
        },

        hasSnippetChanged(snippet) {
            return snippet.key !== snippet.origKey || snippet.value !== snippet.origValue;
        },

        canUpdateSnippet(snippet) {
            return (
                this.hasSnippetChanged(snippet) &&
                snippet.key &&
                !snippet.keyError &&
                snippet.value &&
                !snippet.valueError
            );
        },

        saveButtonPopover(snippet) {
            if (snippet.keyError || snippet.valueError) {
                const err = [];
                if (snippet.keyError) {
                    err.push(`This snippet has an invalid key: ${snippet.keyError}.`);
                }
                if (snippet.valueError) {
                    err.push(`This snippet has an invalid value: ${snippet.valueError}.`);
                }
                return err.join('\n');
            } else if (this.hasSnippetChanged(snippet)) {
                return this.errorMessages.unsavedChanges;
            } else {
                return this.errorMessages.unchangedSnippet;
            }
        },

        snippetKeyChanged(snippet, key) {
            snippet.key = key;

            const index = this.newSnippets.indexOf(snippet);
            if (index > -1) {
                this.$set(this.newSnippets, index, snippet);
            }

            if (snippet.key.match(/\s/)) {
                snippet.keyError = this.errorMessages.spacesInKey;
            } else if (snippet.key.length === 0) {
                snippet.keyError = this.errorMessages.emptyKey;
            } else if (
                snippet.key !== snippet.origKey &&
                this.allSnippets.some(snip => snip !== snippet && snip.key === snippet.key)
            ) {
                snippet.keyError = this.errorMessages.duplicateKey;
            } else {
                snippet.keyError = '';
            }
        },

        snippetValueChanged(snippet, value) {
            snippet.value = value;

            const index = this.newSnippets.indexOf(snippet);
            if (index > -1) {
                this.$set(this.newSnippets, index, snippet);
            }

            if (snippet.value.length === 0) {
                snippet.valueError = this.errorMessages.emptyValue;
            } else {
                snippet.valueError = '';
            }
        },

        clickSaveSnippet(index) {
            this.$refs[`snippetSaveButton-${index}`].onClick();
        },

        saveSnippet(snippet) {
            if (!this.canUpdateSnippet(snippet)) {
                throw new Error(this.saveButtonPopover(snippet));
            }

            const data = { key: snippet.key, value: snippet.value };

            if (snippet.id == null) {
                return this.$http.put('/api/v1/snippet', data).then(response => {
                    const index = this.newSnippets.indexOf(snippet);
                    if (index > -1) {
                        this.newSnippets.splice(index, 1);
                    }
                    this.addSnippetToStore(response.data);
                });
            } else {
                return this.$http.patch(`/api/v1/snippets/${snippet.id}`, data).then(() => {
                    this.updateSnippetInStore(snippet);
                });
            }
        },

        deleteSnippet(snippet) {
            if (snippet.id == null) {
                return Promise.resolve();
            } else {
                return this.$http.delete(`/api/v1/snippets/${snippet.id}`);
            }
        },

        afterDeleteSnippet(snippet, index) {
            if (snippet.id == null) {
                this.newSnippets.splice(index - this.storedSnippets.length, 1);
            } else {
                this.deleteSnippetFromStore(snippet);
            }
        },

        resetSnippet(snippet) {
            snippet.key = snippet.origKey;
            snippet.value = snippet.origValue;
            snippet.keyError = '';
            snippet.valueError = '';
        },
    },

    async mounted() {
        await this.refreshSnippets();
        this.loading = false;
    },

    components: {
        Icon,
        Loader,
        SubmitButton,
    },
};
</script>

<style lang="less" scoped>
.filter-group {
    padding: 0.75rem;
}

.snippets-table {
    margin-bottom: 0;
}

.form-group {
    margin-bottom: 0;
}

.global {
    text-align: right;
    padding-right: 0.9rem;
}
</style>

<style lang="less">
table.snippets-table tr th:first-child {
    width: 25%;
}

table.snippets-table tr th:nth-child(2) {
    width: 60%;
}
</style>
