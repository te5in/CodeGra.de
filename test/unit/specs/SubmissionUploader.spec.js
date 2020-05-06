/* SPDX-License-Identifier: AGPL-3.0-only */
import moment from 'moment';
import { store } from '@/store';

import { Submission, makeUser as makeUserModel } from '@/models';
import * as mutationTypes from '@/store/mutation-types';

import { getCoolOffPeriodText } from '@/components/SubmissionUploader';

import * as utils from '@/utils/typed';

describe('getCoolOffPeriodText', () => {
    let loggedIn;
    let now;

    function makeSub(data) {
        return Submission.fromServerData(Object.assign({
            created_at: now.toISOString(),
            user: { user: { id: loggedIn } },
        }, data));
    }

    function call({
        subs,
        author = loggedIn,
        loggedInUser = loggedIn,
        period = moment.duration({ minutes: 5 }),
        amountInPeriod = 2,
        givenNow,
    }) {
        const user = { user: { id: author.id }};
        return getCoolOffPeriodText({
            subs: subs == null ? utils.range(amountInPeriod).map(() => makeSub(user)) : subs,
            author,
            loggedInUser,
            period,
            amountInPeriod,
            now: givenNow || now,
        });
    }

    function makeUser(data) {
        return makeUserModel(Object.assign({
            id: Math.random(),
        }, data));
    }

    beforeEach(() => {
        now = moment();

        store.getters = {
            'users/getUser': jest.fn(),
        };
        store.commit = jest.fn();

        utils.htmlEscape = jest.fn(x => `|${x}|`);
        utils.numberToTimes = jest.fn(x => `[${x}]`);

        loggedIn = makeUser({ username: 'LOGGED_IN' });
    });

    it('should only show period when you have no/too few submissions', () => {
        [[], [makeSub()]].forEach(subs => {
            expect(call({
                subs,
            })).toBe('You may submit <b>|[2]| every |5 minutes|</b>.');
        });
    });

    it('should use "you" if the logged in user is the author user', () => {
        expect(call({})).toEqual(expect.stringContaining('You submitted'));
        expect(call({amountInPeriod: 1})).toEqual(expect.stringContaining('Your latest submission'));
    });

    it("should use 'your group' if the logged in user's group is the author", () => {
        const data = {
            author: makeUser({
                id: 10,
                group: {
                    id: 5,
                    name: 'NOT_USED',
                    members: [loggedIn],
                },
            })
        }

        expect(call(data)).toEqual(expect.stringContaining('Your group submitted'));

        data.amountInPeriod = 1;
        expect(call(data)).toEqual(expect.stringContaining("Your group's latest"));
    });

    it('should use the author name if the logged in user is NOT the author', () => {
        const data = {
            author: makeUser({
                id: 15,
                // This `a_` should stay lowercase, as we don't want to touch
                // names of users.
                name: 'a_NICE_NAME',
                username: 'A_USERNAME',
            }),
        };
        expect(call(data)).toEqual(expect.stringContaining('|a_NICE_NAME| submitted'));

        data.amountInPeriod = 1;
        expect(call(data)).toEqual(expect.stringContaining("|a_NICE_NAME|'s latest submission"));
    });

    it('should use "the group" if the author is a group and the logged in user is NOT part of that group', () => {
        const data = {
            author: makeUser({
                id: 15,
                name: 'A_GARBLED_GROUP_NAME',
                username: 'A_USERNAME',
                group: {
                    name: 'a_NICE_GROUP_NAME',
                    members: [makeUser()],
                },
            }),
        };
        expect(call(data)).toEqual(expect.stringContaining('The group submitted'));

        data.amountInPeriod = 1;
        expect(call(data)).toEqual(expect.stringContaining("The group's latest"));
    });

    it('should use latest and `numberToTimes` correctly', () => {
        expect(call({
            amountInPeriod: 1,
        })).toEqual(expect.stringContaining('. Your latest submission was |a few seconds ago|'));

        expect(call({
            amountInPeriod: 5,
        })).toEqual(expect.stringContaining('. You submitted |[5]| in the past |few seconds|'));
    });

    it('should show the correct wait time', () => {
        expect(call({})).toEqual(expect.stringContaining(', therefore you must wait for <b>|5 minutes|</b>.'))

        expect(call({
            subs: [makeSub({ created_at: moment().add(-2, 'minutes').toISOString() }), makeSub()]
        })).toEqual(expect.stringContaining(', therefore you must wait for <b>|3 minutes|</b>'))

        // Another user, so it should not mention you again.
        expect(call({
            subs: [makeSub({ created_at: moment().add(-4.9, 'minutes').toISOString() }), makeSub()],
            author: makeUser(),
        })).toEqual(expect.stringContaining(', therefore must wait for <b>|a few seconds|</b>'))
    });

    it('should not show that you cannot submit again, if last submission was old', () => {
        expect(call({
            amountInPeriod: 1,
            subs: [makeSub({ created_at: moment().add(-10, 'minutes').toISOString() })],
        })).toEndWith('Your latest submission was |10 minutes ago|.');
    });
});
