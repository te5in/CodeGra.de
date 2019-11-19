import store from '@/store/modules/submissions';
import * as types from '@/store/mutation-types';
import * as utils from '@/utils';
import axios from 'axios';

function createState() {
    const user = { id: 1000 };
    const submissions = {
        2: [
            { id: 1, user, assignment_id: 2 },
            { id: 2, user, assignment_id: 2 },
            { id: 3, user, assignment_id: 2 },
            { id: 4, user, assignment_id: 2 },
        ],
    };

    return {
        submissions,
        latestSubmissions: {
            2: [submissions[2][0]],
        },
        submissionsByUser: {
            2: {
                1000: submissions[2].slice(),
            },
        },
        submissionsLoaders: {},
        groupSubmissionUsers: {},
    };
};

const mockFormatGrade = jest.fn();
const mockAxiosGet = jest.fn();
axios.get = mockAxiosGet;

utils.formatGrade = mockFormatGrade;

describe('mutations', () => {
    let state;
    beforeEach(() => {
        state = createState();
    })

    describe('set submissions promise', () => {
        it('should set the state prop with correct key', () => {
            const obj1 = {};
            const obj2 = {};

            store.mutations[types.SET_SUBMISSIONS_PROMISE](state, { promise: obj1, assignmentId: 2 });
            expect(state.submissionsLoaders).toEqual({
                2: obj1,
            });

            store.mutations[types.SET_SUBMISSIONS_PROMISE](state, { promise: obj2, assignmentId: 3 });
            expect(state.submissionsLoaders).toEqual({
                2: obj1,
                3: obj2,
            });
        });
    });

    describe('add submission', () => {
        it('should work and have correct order', () => {
            const obj1 = {id: 1, user: { id: 1001 }, assignment_id: 2};
            const obj2 = {id: 2, user: { id: 1001 }, assignment_id: 2};
            const obj3 = {id: 3, user: { id: 1001 }, assignment_id: 2};
            state.submissions[2] = [obj1, obj2];

            store.mutations[types.ADD_SINGLE_SUBMISSION](state, { assignmentId: 2, submission: obj3 });
            expect(state.submissions[2]).toEqual([obj1, obj2, obj3]);
        });

        it('should work when assignment has no submissions', () => {
            const obj = {id: 1, user: { id: 1001 }, assignment_id: 2};
            delete state.submissions[2];

            store.mutations[types.ADD_SINGLE_SUBMISSION](state, { assignmentId: 2, submission: obj });
            expect(state.submissions[2]).toEqual([obj]);
        });
    });

    describe('update submission', () => {
        it('should work for normal props', () => {
            const obj1 = {id: 1, user: { id: 1001 }, assignment_id: 2};
            const obj2 = {id: 2, user: { id: 1001 }, assignment_id: 2};
            const obj3 = {id: 3, user: { id: 1001 }, assignment_id: 2};
            state.submissions[2] = [obj1, obj2, obj3];

            store.mutations[types.UPDATE_SUBMISSION](state, {
                assignmentId: 2,
                submissionId: 2,
                submissionProps: { feedback: 'xxx' },
            });
            expect(state.submissions[2]).toEqual([
                obj1,
                obj2,
                obj3,
            ]);
            expect(obj2).toHaveProperty('feedback', 'xxx');
        });

        it('should work for not unknown submissions', () => {
            const obj1 = {id: 1, user: { id: 1001 }, assignment_id: 2};
            const obj2 = {id: 2, user: { id: 1001 }, assignment_id: 2};
            const obj3 = {id: 3, user: { id: 1001 }, assignment_id: 2};
            state.submissions[2] = [obj1, obj2, obj3];

            expect(
                () => store.mutations[types.UPDATE_SUBMISSION](state, { assignmentId: 2, submissionId: 'UNKNOWN', submissionProps: { name: 4 } }),
            ).toThrow();
        });

        it('should work for not work for id', () => {
            const obj1 = {id: 1, user: { id: 1001 }, assignment_id: 2};
            const obj2 = {id: 2, user: { id: 1001 }, assignment_id: 2};
            const obj3 = {id: 3, user: { id: 1001 }, assignment_id: 2};
            state.submissions[2] = [obj1, obj2, obj3];

            expect(
                () => store.mutations[types.UPDATE_SUBMISSION](state, { assignmentId: 2, submissionId: 2, submissionProps: { id: 4 } }),
            ).toThrow();
        });

        it('grade prop should be formatted', () => {
            mockFormatGrade.mockClear();
            const single1 = {};
            const single2 = {};
            mockFormatGrade.mockReturnValueOnce(single2);

            const obj1 = {id: 1, user: { id: 1001 }, assignment_id: 2};
            const obj2 = {id: 2, user: { id: 1001 }, assignment_id: 2};
            const obj3 = {id: 3, user: { id: 1001 }, assignment_id: 2};
            state.submissions[2] = [obj1, obj2, obj3];

            store.mutations[types.UPDATE_SUBMISSION](state, { assignmentId: 2, submissionId: 2, submissionProps: { grade: single1 } });
            expect(state.submissions[2]).toEqual([
                obj1,
                obj2,
                obj3,
            ]);
            expect(obj2).toHaveProperty('grade', single2);

            expect(mockFormatGrade).toBeCalledTimes(1);
            expect(mockFormatGrade).toBeCalledWith(single1);
        });
    });
});

describe('actions', () => {
    let state;
    let mockDispatch;
    let mockCommit;
    let context;

    beforeEach(() => {
        state = createState();
        mockDispatch = jest.fn();
        mockCommit = jest.fn();
        context = {
            state,
            dispatch: mockDispatch,
            commit: mockCommit,
        };
    });

    describe('load submissions', () => {
        it('should reload submissions', async () => {
            const obj1 = {};
            const obj2 = {};
            mockDispatch.mockReturnValueOnce(obj1);

            await store.actions.loadSubmissions(context, obj2);

            expect(mockDispatch).toBeCalledTimes(1);
            expect(mockDispatch).toBeCalledWith('forceLoadSubmissions', obj2);
        });

        it('should return submissions promise', async () => {
            const obj1 = {};
            const obj2 = {};
            state.submissionsLoaders[obj2] = obj1;

            await expect(store.actions.loadSubmissions(context, obj2)).resolves.toBe(obj1);

            expect(mockDispatch).not.toBeCalled();
            expect(mockCommit).not.toBeCalled();
        });
    });

    describe('update submission', () => {
        it('should simply work', () => {
            const props = {};
            const data = {
                assignmentId: 2,
                submissionId: 4,
                submissionProps: props,
                other: 4,
            };
            store.actions.updateSubmission(context, data);

            expect(mockCommit).toBeCalledTimes(1);
            expect(mockCommit).toBeCalledWith(types.UPDATE_SUBMISSION, {
                assignmentId: 2,
                submissionId: 4,
                submissionProps: props,
            });
        });
    });

    describe('add submission', () => {
        it('should simply work', () => {
            mockFormatGrade.mockClear();
            const single1 = {a: 1};
            const single2 = {b: 2};
            const props = {
                grade: single1,
                anything: 5,
            };
            const data = {
                assignmentId: 2,
                submissionId: 4,
                submission: props,
            };
            mockFormatGrade.mockReturnValueOnce(single2);

            store.actions.addSubmission(context, data);

            expect(mockCommit).toBeCalledTimes(1);
            expect(mockCommit).toBeCalledWith(types.ADD_SINGLE_SUBMISSION, {
                submission: {
                    formatted_created_at: expect.any(String),
                    grade: single2,
                    anything: 5,
                },
            });
            expect(mockFormatGrade).toBeCalledTimes(1);
            expect(mockFormatGrade).toBeCalledWith(single1);
        });
    });
});
