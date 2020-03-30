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
            console.log('resetting', this.error);
            this.error = null;
            this.$emit('reset');
        },
    },

    errorCaptured(error) {
        console.log('error captured', error);
        this.error = error;
        this.$emit('error', error);
        return this.capture ? false : undefined;
    },

    render() {
        if (this.error != null && this.$scopedSlots.error != null) {
            return this.$scopedSlots.error({
                error: this.error,
                resetError: this.reset,
            });
        }
        return this.$scopedSlots.default({
            error: this.error,
            resetError: this.reset,
        });
    },
};
