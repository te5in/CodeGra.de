import { config } from '@vue/test-utils';
import axios from 'axios';

config.mocks.$http = axios;
global.UserConfig = {
    features: {
        rubrics: true,
    },
};

global.log = console.log;
