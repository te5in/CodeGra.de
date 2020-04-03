<template>
<div class="user-notifications">
    <b-collapse :visible="showSettings">
        <div class="border-bottom notification-settings-wrapper">
            <notification-settings class="px-3 pt-3" />
        </div>
    </b-collapse>

    <cg-loader v-if="loading"
               :scale="1"
               class="p-3"/>
    <div v-else class="p-3">
        <div v-if="!hasUnreadNotifications"
             class="text-muted">
            You are all caught up!
            <hr v-if="hasReadNotifications"  />
        </div>

        <div class="border rounded" v-if="notifications.length > 0">
            <table class="table table-hover table-borderless mb-0">
                <transition-group name="fade" tag="tbody">
                    <user-notification :notification="notification"
                                       class="cursor-pointer"
                                       @click.native="gotoNotification(notification)"
                                       :class="{ read: notification.read }"
                                       v-for="notification in notifications"
                                       :key="notification.id" />
                </transition-group>
            </table>
        </div>

        <div v-if="hasReadNotifications && !showRead"
             class="d-flex justify-content-center mt-3">
            <b-btn @click="showRead = true">
                Show read notifications
            </b-btn>
        </div>
    </div>
</div>
</template>

<script lang="ts">
import { Vue, Component, Prop } from 'vue-property-decorator';

import { NotificationStore } from '@/store/modules/notification';

import * as models from '@/models';

import UserNotification from './UserNotification';
import NotificationSettings from './NotificationSettings';

@Component({
    components: {
        UserNotification,
        NotificationSettings,
    },
})
export default class UserNotifications extends Vue {
    @Prop({ required: true }) showSettings!: boolean;

    // eslint-disable-next-line
    get allNotifications(): ReadonlyArray<models.Notification> {
        return NotificationStore.getAllNotifications();
    }

    // eslint-disable-next-line
    get unreadNotifications(): ReadonlyArray<models.Notification> {
        return NotificationStore.getAllUnreadNotifications();
    }

    // eslint-disable-next-line
    get hasUnreadNotifications(): boolean {
        return NotificationStore.getHasUnreadNotifications();
    }

    get hasReadNotifications() {
        return this.allNotifications.length > this.unreadNotifications.length;
    }

    get notifications() {
        return this.showRead ? this.allNotifications : this.unreadNotifications;
    }

    loading: boolean = true;

    smallLoading: boolean = false;

    showRead: boolean = false;

    isDestroyed: boolean = false;

    destroyed() {
        this.$root.$loadFullNotifications = false;
        this.isDestroyed = true;
    }

    async created() {
        this.loading = true;
        this.$root.$loadFullNotifications = true;
        await NotificationStore.dispatchLoadNotifications();
        this.loading = false;
    }

    // eslint-disable-next-line class-methods-use-this
    getNotificationRoute(notification: models.Notification): Object {
        return {
            name: 'submission_file',
            params: {
                courseId: `${notification.assignment?.courseId}`,
                assignmentId: `${notification.assignment?.id}`,
                submissionId: `${notification.submission?.id}`,
                fileId: notification.fileId,
            },
            query: {
                replyToFocus: `${notification.commentReply?.id}`,
            },
            hash: '#code',
        };
    }

    async gotoNotification(notification: models.Notification): Promise<void> {
        const assignmentId = notification.assignment?.id;
        const submissionId = notification.submission?.id;

        this.$store.dispatch('feedback/loadFeedback', {
            assignmentId,
            submissionId,
            force: true,
        });

        notification.markAsRead().then(({ cgResult }) => {
            NotificationStore.commitUpdateNotifications({
                notifications: [cgResult],
            });
        });

        this.$router.push(this.getNotificationRoute(notification));
        this.$root.$emit('cg::sidebar::close');
    }
}
</script>

<style lang="less" scoped>
@import '~mixins.less';

.notification-settings-wrapper {
    background-color: @footer-color;
}

.list-group-item:hover {
    background-color: @color-lightest-gray;
}

.list-group-item.read {
    background-color: @color-lighter-gray;
    &:hover {
        background-color: darken(@color-lighter-gray, 5%);
    }
}

.fade-enter-active,
.fade-leave-active {
    transition: opacity @transition-duration;
}
.fade-enter,
.fade-leave-to {
    opacity: 0;
}
</style>
