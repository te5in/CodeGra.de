/* SPDX-License-Identifier: AGPL-3.0-only */
import Vue from 'vue';

export default Vue.extend({
    name: 'cg-logo',
    functional: true,

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

    render(h, ctx) {
        function getLogoSrc(): string {
            let logo;
            const now = ctx.parent.$root.$now;
            const isChristmas = () => now.month() === 11 && now.date() <= 26;

            if (ctx.props.showEasterEggs && isChristmas()) {
                logo = 'CodeGrade_christmas';
            } else if (ctx.props.small) {
                logo = 'logo';
            } else {
                logo = 'codegrade';
            }

            if (ctx.props.inverted) {
                logo += '-inv';
            }

            return `/static/img/${logo}.svg`;
        }
        let staticClass = 'cg-logo';
        if (ctx.data.staticClass) {
            staticClass = `${staticClass} ${ctx.data.staticClass}`;
        }

        return h('img', {
            attrs: Object.assign(
                {
                    src: getLogoSrc(),
                    alt: 'CodeGrade',
                },
                ctx.data.attrs,
            ),
            class: [ctx.data.class, staticClass],
            style: [ctx.data.style, ctx.data.staticStyle],
        });
    },
});
