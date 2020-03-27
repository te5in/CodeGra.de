/* eslint-disable prefer-arrow-callback */

import Vue from 'vue';
import { getStoreBuilder } from 'vuex-typex';
import axios, { AxiosResponse } from 'axios';

import { Notification, CommentNotification, CommentNotificationServerData } from '@/models';
import { RootState } from '@/store/state';
import { SubmitButtonResult } from '@/interfaces';

const storeBuilder = getStoreBuilder<RootState>();

export interface NotificationState {
    notifications: Record<string, Notification>;
}

const moduleBuilder = storeBuilder.module<NotificationState>('notification', {
    notifications: {},
});

type NotificationResponseData = { notifications: CommentNotificationServerData[] };
type NotificationResponse = AxiosResponse<NotificationResponseData>;

export namespace NotificationStore {
    export const commitUpdateNotifications = moduleBuilder.commit(
        function commitUpdateNotifications(state, payload: { notifications: Notification[] }) {
            payload.notifications.forEach(n => Vue.set(state.notifications, n.id, n));
        },
        'commitUpdateNotification',
    );

    export const dispatchMarkAllAsRead = moduleBuilder.dispatch(
        async function dispatchMarkAllAsRead(
            _,
            __: void,
        ): Promise<SubmitButtonResult<Notification[], NotificationResponseData>> {
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
        },
        'dispatchMarkAllAsRead',
    );

    export const dispatchLoadNotifications = moduleBuilder.dispatch(
        async function dispatchLoadNotifications(_, __: void) {
            const response: NotificationResponse = await axios.get(
                '/api/v1/notifications/?unread_only=false',
            );

            NotificationStore.commitUpdateNotifications({
                notifications: response.data.notifications.map(n =>
                    CommentNotification.fromServerData(n),
                ),
            });
            return response;
        },
        'dispatchLoadNotifications',
    );

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

    export const getAllUnreadNotifications = moduleBuilder.read(function getAllUnreadNotifications(
        state,
    ) {
        return _getAllNotifications(state).filter(x => !x.read);
    },
    'getAllUnreadNotifications');

    export const getHasUnreadNotifications = moduleBuilder.read(function getHasUnreadNotifications(
        state,
    ) {
        return Object.values(state.notifications).some(x => !x.read);
    },
    'getHasUnreadNotifications');
}
