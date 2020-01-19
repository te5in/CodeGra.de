/* SPDX-License-Identifier: AGPL-3.0-only */
const fs = require('fs');
const ini = require('ini');
const execFileSync = require('child_process').execFileSync;
const moment = require('moment');

function filterKeys(obj, ...keys) {
    return keys.reduce(
        (acc, key) => {
            acc[key] = obj[key];
            return acc;
        },
        {},
    );
}

let userConfig = {};

try {
    userConfig = ini.parse(fs.readFileSync('./config.ini', 'utf-8'));
} catch (err) {
    process.stderr.write('Config file not found, using default values!\n');
}

if (userConfig['Front-end'] === undefined) userConfig['Front-end'] = {};
if (userConfig.Features === undefined) userConfig.Features = {};
if (userConfig.AutoTest === undefined) userConfig.AutoTest = {};

const config = Object.assign({}, {
    email: 'info@CodeGra.de',
    maxLines: 2500,
}, userConfig['Front-end']);

const version = execFileSync('git', ['describe', '--abbrev=0', '--tags']).toString().trim();
const tagMsg = execFileSync('git', ['tag', '-l', '-n400', version]).toString().split('\n');
let inCorrectPart = false;
let done = false;
let skip = false;

config.release = {
    version,
    date: process.env.CG_FORCE_BUILD_DATE || moment.utc().toISOString(),
    message: tagMsg.reduce((res, cur) => {
        if (done || skip) {
            skip = false;
        } else if (inCorrectPart && /^ *$/.test(cur)) {
            done = true;
        } else if (inCorrectPart) {
            res.push(cur);
        } else if (/^ *\*\*Released\*\*/.test(cur)) {
            inCorrectPart = true;
            skip = true;
        }
        return res;
    }, []).join(' '),
};

config.features = Object.assign({
    auto_test: false,
    blackboard_zip_upload: true,
    rubrics: true,
    automatic_lti_role: true,
    LTI: true,
    linters: true,
    incremental_rubric_submission: true,
    register: false,
    groups: false,
}, userConfig.Features);

config.autoTest = {
    auto_test_max_command_time: 300,
};

if (Object.hasOwnProperty.call(userConfig.AutoTest, 'auto_test_max_time_command')) {
    config.autoTest.auto_test_max_command_time = Number(userConfig.AutoTest.auto_test_max_time_command);
}

config.proxyUrl = userConfig['Back-end'].external_proxy_url
config.isProduction = process.env.NODE_ENV === 'production';

if (!config.proxyUrl && config.isProduction) {
    throw new Error('Production can only be used with a proxy url.');
}

module.exports = config;
