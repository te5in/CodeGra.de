<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="password-suggestions">
    <p>{{ message }}</p>

    <b v-if="feedback">Suggestions</b>

    <ul v-if="feedback">
        <li v-for="suggestion in suggestions">
            {{ suggestion }}
        </li>
    </ul>
</div>
</template>

<script>
export default {
    name: 'password-suggestions',

    props: {
        error: {
            type: Error,
            required: true,
        },
    },

    computed: {
        feedback() {
            const res = this.error && this.error.response;

            return res && res.data && res.data.feedback;
        },

        message() {
            const err = this.error;

            if (this.feedback) {
                return this.feedback.warning;
            } else if (err.response && err.response.data) {
                return err.response.data.message;
            } else {
                return err.message;
            }
        },

        suggestions() {
            const fb = this.feedback;

            return fb && fb.suggestions;
        },
    },
};
</script>

<style lang="less" scoped>
.password-suggestions {
    text-align: left;

    & > :last-child {
        margin-bottom: 0;
    }
}

ul {
    padding-left: 1rem;
}
</style>
