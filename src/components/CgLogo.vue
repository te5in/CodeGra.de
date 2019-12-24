<template>
    <img class="cg-logo"
         :src="logoSrc"
         alt="CodeGrade" />
</template>

<script>
export default {
    name: 'cg-logo',

    props: {
        inverted: {
            type: Boolean,
            required: true,
        },
        small: {
            type: Boolean,
            default: false,
        },
        showEasterEggs: {
            type: Boolean,
            default: false,
        },
    },

    computed: {
        logoSrc() {
            let logo;

            if (this.showEasterEggs && this.isChristmas) {
                logo = 'CodeGrade_christmas';
            } else if (this.small) {
                logo = 'logo';
            } else {
                logo = 'codegrade';
            }

            if (this.inverted) {
                logo += '-inv';
            }

            return `/static/img/${logo}.svg`;
        },

        isChristmas() {
            return this.$root.$now.month() === 11 && this.$root.$now.date() <= 26;
        },
    },
};
</script>
