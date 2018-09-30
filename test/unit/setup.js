import { config } from '@vue/test-utils';
import '@/polyfills';
import axios from 'axios';

config.mocks.$http = axios;
global.UserConfig = {
    features: {
        rubrics: true,
    },
};

config.mocks.$htmlEscape = jest.fn(a => a);

global.log = console.log;
