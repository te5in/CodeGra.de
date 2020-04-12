/* SPDX-License-Identifier: AGPL-3.0-only */
export default {
    props: {
        capture: {
            type: Boolean,
            default: false,
        },
    },

    data() {
        return {
            error: null,
        };
    },

    methods: {
        reset() {
            this.error = null;
            this.$emit('reset');
        },
    },

    errorCaptured(error) {
        this.error = error;
        this.$emit('error', error);
        return this.capture ? false : undefined;
    },

    render() {
        return this.$scopedSlots.default({
            error: this.error,
            resetError: this.reset,
        });
    },
};
