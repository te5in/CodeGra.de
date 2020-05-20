// SPDX-License-Identifier: AGPL-3.0-only
const defaultLTIProvider = Object.freeze(<const>{
    addBorder: false,
    supportsDeadline: false,
    supportsBonusPoints: false,
    supportsStateManagement: false,
});
type LTIProvider = {
    readonly addBorder: boolean;
    readonly supportsDeadline: boolean;
    readonly supportsBonusPoints: boolean;
    readonly supportsStateManagement: boolean;
};

const copyFreeze = <T>(x: T): Readonly<T> => Object.freeze(Object.assign({}, x));

const blackboardProvider: LTIProvider = copyFreeze(defaultLTIProvider);

const brightSpaceProvider: LTIProvider = copyFreeze(defaultLTIProvider);

const moodleProvider: LTIProvider = copyFreeze(defaultLTIProvider);

const canvasProvider: LTIProvider = Object.freeze(<const>{
    addBorder: true,
    supportsDeadline: true,
    supportsBonusPoints: true,
    supportsStateManagement: true,
});

/* eslint-disable camelcase */
export const LTI1p3ProviderNames = Object.freeze(<const>[
    'Blackboard',
    'Brightspace',
    'Canvas',
    'Moodle',
]);
export type LTI1p3ProviderName = typeof LTI1p3ProviderNames[number];

export interface LTI1p3Capabilities {
    lms: LTI1p3ProviderName;
    set_deadline: boolean;
    set_state: boolean;
    test_student_name: string | null;
    cookie_post_message: string | null;
    supported_custom_replacement_groups: string[];
}
/* eslint-enable camelcase */

export class LTI1p3ProviderCapabilties implements LTIProvider {
    readonly addBorder: boolean;

    readonly supportsDeadline: boolean;

    readonly supportsBonusPoints: boolean;

    readonly supportsStateManagement: boolean;

    constructor(capabilities: LTI1p3Capabilities) {
        this.addBorder = capabilities.lms === 'Canvas';

        this.supportsDeadline = !capabilities.set_deadline;

        this.supportsBonusPoints = false;

        this.supportsStateManagement = !capabilities.set_state;
    }
}

export default {
    Blackboard: blackboardProvider,
    BrightSpace: brightSpaceProvider,
    Canvas: canvasProvider,
    Moodle: moodleProvider,
};
