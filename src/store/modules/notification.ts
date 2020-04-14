/* SPDX-License-Identifier: AGPL-3.0-only */
import Vue from 'vue';
import { getStoreBuilder } from 'vuex-typex';
import axios, { AxiosResponse } from 'axios';

import { Notification, CommentNotification, CommentNotificationServerData } from '@/models';
import { RootState } from '@/store/state';
import { SubmitButtonResult } from '@/interfaces';

const storeBuilder = getStoreBuilder<RootState>();

export interface NotificationState {
    notifications: Record<string, Notification>;
    hasUnread: boolean;
}

const moduleBuilder = storeBuilder.module<NotificationState>('notification', {
    notifications: {},
    hasUnread: false,
});

// eslint-disable-next-line camelcase
type NotificationHasUnreadResponseData = { has_unread: boolean };
type NotificationResponseData = { notifications: CommentNotificationServerData[] };
type NotificationResponse = AxiosResponse<NotificationResponseData>;

export namespace NotificationStore {
    export const commitUpdateNotifications = moduleBuilder.commit(
        (state, payload: { notifications: Notification[] }) => {
            payload.notifications.forEach(n => Vue.set(state.notifications, n.id, n));
            state.hasUnread = payload.notifications.some(x => !x.read);
        },
        'commitUpdateNotification',
    );

    export const commitUpdateHasUnread = moduleBuilder.commit(
        (state, payload: { hasUnread: boolean }) => {
            state.hasUnread = payload.hasUnread;
        },
        'commitUpdateHasUnread',
    );

    export const commitClearNotifications = moduleBuilder.commit(state => {
        state.notifications = {};
        state.hasUnread = false;
    }, 'commitClearNotifications');

    export const dispatchMarkAllAsRead = moduleBuilder.dispatch(async (_, __: void): Promise<
        SubmitButtonResult<Notification[], NotificationResponseData>
    > => {
        const response: NotificationResponse = await axios.patch('/api/v1/notifications/', {
            notifications: NotificationStore.getAllUnreadNotifications().map(r => ({
                id: r.id,
                read: true,
            })),
        });

        const notifications = response.data.notifications.map(n =>
            CommentNotification.fromServerData(n),
        );

        return {
            ...response,
            cgResult: notifications,
            onAfterSuccess: () => {
                NotificationStore.commitUpdateNotifications({ notifications });
            },
        };
    }, 'dispatchMarkAllAsRead');

    export const dispatchLoadHasUnread = moduleBuilder.dispatch(async (_, __: void) => {
        //
        const response: AxiosResponse<NotificationHasUnreadResponseData> = await axios.get(
            '/api/v1/notifications/?has_unread',
        );

        NotificationStore.commitUpdateHasUnread({ hasUnread: response.data.has_unread });
    }, 'dispatchLoadHasUnread');

    export const dispatchLoadNotifications = moduleBuilder.dispatch(async (_, __: void) => {
        const response: NotificationResponse = await axios.get('/api/v1/notifications/');

        NotificationStore.commitUpdateNotifications({
            notifications: response.data.notifications.map(n =>
                CommentNotification.fromServerData(n),
            ),
        });
        return response;
    }, 'dispatchLoadNotifications');

    // eslint-disable-next-line
    function _getAllNotifications(state: NotificationState): ReadonlyArray<Notification> {
        return Object.values(state.notifications).sort(
            (a, b) => b.createdAt.valueOf() - a.createdAt.valueOf(),
        );
    }

    export const getAllNotifications = moduleBuilder.read(
        _getAllNotifications,
        'getAllNotifications',
    );

    export const getAllUnreadNotifications = moduleBuilder.read(
        state => _getAllNotifications(state).filter(x => !x.read),
        'getAllUnreadNotifications',
    );

    export const getHasUnreadNotifications = moduleBuilder.read(
        state => state.hasUnread,
        'getHasUnreadNotifications',
    );
}
