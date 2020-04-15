/* SPDX-License-Identifier: AGPL-3.0-only */
import axios, { AxiosResponse } from 'axios';

import { NotificationReason } from './notification';

export type EmailNotificationType = 'off' | 'direct' | 'daily' | 'weekly';

interface NotificationSettingOptionJSON {
    reason: NotificationReason;
    explanation: string;
    value: EmailNotificationType;
}

interface NotificationSettingJSON {
    options: NotificationSettingOptionJSON[];
    // eslint-disable-next-line camelcase
    possible_values: EmailNotificationType[];
}

function getUrl(token: string | null) {
    const base = '/api/v1/settings/notification_settings/';
    if (token != null) {
        return `${base}?token=${token}`;
    }
    return base;
}

export class NotificationSetting {
    // eslint-disable-next-line
    constructor(
        public readonly reason: NotificationReason,
        public readonly explanation: string,
        // eslint-disable-next-line
        public value: EmailNotificationType) { }

    static fromServerData(data: NotificationSettingOptionJSON): NotificationSetting {
        return new NotificationSetting(data.reason, data.explanation, data.value);
    }

    updateValue(newValue: EmailNotificationType, token: string | null = null): Promise<void> {
        return axios
            .patch(getUrl(token), {
                reason: this.reason,
                value: newValue,
            })
            .then(() => {
                this.value = newValue;
            });
    }
}

export class NotificationSettings {
    constructor(
        public readonly settings: NotificationSetting[],
        public readonly possibleValues: EmailNotificationType[],
    ) {
        Object.freeze(this);
    }

    static async loadFromServer(token: string | null = null): Promise<NotificationSettings> {
        const url = getUrl(token);

        const { data }: AxiosResponse<NotificationSettingJSON> = await axios.get(url);
        return new NotificationSettings(
            data.options.map(NotificationSetting.fromServerData),
            data.possible_values,
        );
    }
}
