/* SPDX-License-Identifier: AGPL-3.0-only */
import 'vue';
import { Moment } from 'moment';
import { AxiosStatic } from 'axios';
import * as typedUtils from '@/utils/typed';
import UserConfig from './userConfig';

// 2. Specify a file with the types you want to augment
//    Vue has the constructor type in types/vue.d.ts
declare module 'vue/types/vue' {
    // 3. Declare augmentation for Vue
    interface Vue {
        $afterRerender(): Promise<void>;
        $http: AxiosStatic;
        $utils: typeof typedUtils;
        $now: Moment;

        $loadFullNotifications: boolean;
        $userConfig: typeof UserConfig;
    }
}
