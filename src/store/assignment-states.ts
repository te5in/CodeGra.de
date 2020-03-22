/* SPDX-License-Identifier: AGPL-3.0-only */

export const HIDDEN = 'hidden';
export const SUBMITTING = 'submitting';
export const GRADING = 'grading';
export const OPEN = 'open';
export const DONE = 'done';

export type AssignmentStates =
    | typeof HIDDEN
    | typeof SUBMITTING
    | typeof GRADING
    | typeof OPEN
    | typeof DONE;
