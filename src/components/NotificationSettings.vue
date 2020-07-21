<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="notification-settings">
    <b-alert v-if="error" show variant="danger">
        {{ $utils.getErrorMessage(error) }}
    </b-alert>
    <cg-loader v-else-if="loading" :scale="1"/>
    <div v-else>
        <h5>
            Feedback
            <cg-description-popover hug-text>
                With these settings you can determine when you should get an
                email notification when somebody creates a new comment. The
                possible options are:
                <ul class="feedback-notification-options-list">
                    <li>
                        <b>direct</b>: Send an email as soon as a new comment is placed.
                    </li>
                    <li>
                        <b>daily</b>: Send a daily digest email with all new
                        comments. If there are no new comments no email is sent.
                    </li>
                    <li>
                        <b>weekly</b>: Same as the <b>daily</b>, but send a
                        weekly digest.
                    </li>
                    <li>
                        <b>off</b>: Never notify me.
                    </li>
                </ul>
            </cg-description-popover>
        </h5>
        <hr class="mb-2">
        <table class="table table-borderless m-0 border-0">
            <tr v-for="setting in settings.settings"
                :key="setting.reason">
                <td>
                    <b-badge>
                        {{ setting.reason }}
                    </b-badge>
                    <cg-description-popover hug-text>
                        What to do when you get a notification because
                        {{ setting.explanation }}.
                    </cg-description-popover>
                </td>
                <td class="select-col">
                    <span v-if="saveSettingsErrors[setting.reason]"
                          class="error-icon">
                        <icon name="times" class="text-danger"
                              :id="`${baseId}-${setting.reason}`"/>
                        <b-popover :target="`${baseId}-${setting.reason}`"
                                   show
                                   triggers="focus"
                                   @hidden="hideError(setting)">
                            <icon name="times"
                                  class="hide-button"
                                  @click.native="hideError(setting)"/>
                            <span>
                                {{ $utils.getErrorMessage(saveSettingsErrors[setting.reason]) }}
                            </span>
                        </b-popover>
                    </span>
                    <cg-loader :scale="1" v-else-if="loadingSettings[setting.reason]"/>
                    <b-form-select :options="settings.possibleValues"
                                   :style="{ opacity: showSelect(setting) ? 1 : 0 }"
                                   :value="setting.value"
                                   @input="updateSetting(setting, $event)"
                                   @click.native.stop/>
                </td>
            </tr>
        </table>
    </div>
</div>
</template>

<script lang="ts">

// @ts-ignore
import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/times';

import { Vue, Component, Prop } from 'vue-property-decorator';

import * as models from '@/models';

@Component({ components: { Icon } })
export default class NotificationSettings extends Vue {
    @Prop({ default: null }) token!: string | null;

    public settings: models.NotificationSettings | null = null;

    public error: Object | null = null;

    public loadingSettings: Record<string, boolean> = {};

    public saveSettingsErrors: Record<string, boolean> = {};

    public baseId: string = `notification-settings-${this.$utils.getUniqueId()}`;

    get loading(): boolean {
        return this.settings == null;
    }

    created() {
        this.load();
    }

    async load() {
        this.settings = null;
        this.error = null;

        try {
            this.settings = await models.NotificationSettings.loadFromServer(this.token);
        } catch (e) {
            this.error = e;
        }
    }

    async updateSetting(
        setting: models.NotificationSetting,
        newValue: models.EmailNotificationType,
    ): Promise<void> {
        this.$set(this.loadingSettings, setting.reason, true);
        try {
            await this.$utils.waitAtLeast(250, setting.updateValue(newValue, this.token));
        } catch (e) {
            this.$set(this.saveSettingsErrors, setting.reason, e);
            await this.$nextTick();
        }
        this.$set(this.loadingSettings, setting.reason, false);
    }

    hideError(setting: models.NotificationSetting) {
        this.$delete(this.saveSettingsErrors, setting.reason);
    }

    showSelect(setting: models.NotificationSetting): boolean {
        const reason = setting.reason;
        return this.saveSettingsErrors[reason] == null && !this.loadingSettings[reason];
    }
}
</script>

<style lang="less" scoped>
@import "~mixins.less";

td {
    vertical-align: middle;
}
.badge {
    text-transform: uppercase;
    font-size: 70%;
}

.select-col {
    position: relative;

    .error-icon,
    .loader {
        position: absolute;
        right: 0%;
        top: 50%;
        line-height: 1;
        transform: translate(-0.75rem, -50%);
    }
}

.select-col select,
.feedback-notification-options-list b {
    text-transform: uppercase;
    font-size: 80%;
}

.notification-settings {
    .default-background;
}
</style>
