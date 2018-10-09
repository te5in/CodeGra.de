/* SPDX-License-Identifier: AGPL-3.0-only */
export const pageTitleSep = '»';
let changed = false;

export function setPageTitle(title = '') {
    changed = true;
    let s = title;
    if (s) s += ` ${pageTitleSep} `;
    document.title = `${s}CodeGra.de`;
}

export function resetPageTitle() {
    changed = false;
    setTimeout(() => {
        if (!changed) {
            setPageTitle();
        }
    }, 500);
}
