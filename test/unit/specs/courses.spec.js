import store from '@/store/modules/courses';
import * as types from '@/store/mutation-types';
import * as utils from '@/utils';
import axios from 'axios';

function createState() {
    return {
        courses: {
            1: {
                assignments: [{
                    id: 2,
                    name: '2',
                }, {
                    id: 3,
                    name: '3',
                }],
                name: 'hello',
            },
            4: {
                assignments: [{
                    id: 5,
                    name: '5',
                }],
                name: 'bye',
            },
        },
        currentCourseLoader: null,
    };
};

const mockFormatGrade = jest.fn();
const mockAxiosGet = jest.fn();
axios.get = mockAxiosGet;

utils.formatGrade = mockFormatGrade;

describe('getters', () => {
    let state;

    beforeEach(() => {
        state = createState();
    });

    describe('courses', () => {
        it('should return the state object', () => {
            expect(store.getters.courses(state)).toBe(state.courses);
        });
    });

    describe('assignments', () => {
        it('should work without courses', () => {
            expect(store.getters.assignments({})).toEqual({});
        });
        it('should work with courses', () => {
            expect(store.getters.assignments(state)).toEqual({
                2: {
                    id: 2,
                    name: '2',
                },
                3: {
                    id: 3,
                    name: '3',
                },
                5: {
                    id: 5,
                    name: '5',
                },
            });
        });
    });
});

describe('mutations', () => {
    let state;
    beforeEach(() => {
        state = createState();
    })

    describe('clear courses', () => {
        it('should clear all the things', () => {
            store.mutations[types.CLEAR_COURSES](state);
            expect(state).toEqual({
                courses: {},
                currentCourseLoader: null,
            });
        });
    });

    describe('update course', () => {
        it('should not work for id', () => {
            expect(
                () => store.mutations[types.UPDATE_COURSE](
                    state, { courseId: 1, courseProps: { id: 5 }},
                ),
            ).toThrow();
        });

        it('should not work for new props', () => {
            expect(
                () => store.mutations[types.UPDATE_COURSE](
                    state, { courseId: 1, courseProps: { newProp: 5 }},
                ),
            ).toThrow();
        });

        it('should not work for unknown courses', () => {
            expect(
                () => store.mutations[types.UPDATE_COURSE](
                    state, { courseId: 'UNKOWN', courseProps: { name: 5 }},
                ),
            ).toThrow();
        });

        it('should work for known props', () => {
            store.mutations[types.UPDATE_COURSE](
                state,
                { courseId: 1, courseProps: { name: 5 }},
            );
            expect(state.courses[1].name).toBe(5);
            expect(state.courses[4].name).toBe('bye');
        });
    });


    describe('update assignment', () => {
        it('should not work for id', () => {
            expect(
                () => store.mutations[types.UPDATE_ASSIGNMENT](
                    state, { assignmentId: 2, assignmentProps: { id: 5 }},
                ),
            ).toThrow();
        });

        it('should not work for new props', () => {
            expect(
                () => store.mutations[types.UPDATE_ASSIGNMENT](
                    state, { assignmentId: 2, assignmentProps: { newProp: 5 }},
                ),
            ).toThrow();

            expect(
                () => store.mutations[types.UPDATE_ASSIGNMENT](
                    state, { assignmentId: 2, assignmentProps: { submission: 5 }},
                ),
            ).toThrow();
        });

        it('should work for some unknown props', () => {
            ['rubric', 'graders'].forEach((key) => {
                const obj1 = {};

                store.mutations[types.UPDATE_ASSIGNMENT](
                    state,
                    { assignmentId: 2, assignmentProps: { [key]: obj1 }},
                );

                expect(state.courses[1].assignments[0][key]).toBe(obj1);
                expect(state.courses[1].assignments[1][key]).not.toBe(obj1);
            });
        });


        it('should not work for unknown assignments', () => {
            expect(
                () => store.mutations[types.UPDATE_ASSIGNMENT](
                    state, { courseId: 'UNKOWN', assignmentProps: { name: 5 }},
                ),
            ).toThrow();
        });

        it('should work for known props', () => {
            store.mutations[types.UPDATE_ASSIGNMENT](
                state,
                { assignmentId: 2, assignmentProps: { name: 5 }},
            );
            expect(state.courses[1].assignments[0].name).toBe(5);
            expect(state.courses[1].assignments[1].name).toBe('3');
        });
    });

    describe('set course promise', () => {
        it('should set the state prop', () => {
            const obj1 = {};
            store.mutations[types.SET_COURSES_PROMISE](state, obj1);
            expect(state.currentCourseLoader).toBe(obj1);
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

    describe('load courses', () => {
        it('should reload courses', async () => {
            const obj1 = {};
            mockDispatch.mockReturnValueOnce(obj1);

            await store.actions.loadCourses(context);

            expect(mockDispatch).toBeCalledTimes(1);
            expect(mockDispatch).toBeCalledWith('reloadCourses');
            expect(mockCommit).toBeCalledTimes(1);
            expect(mockCommit).toBeCalledWith(types.SET_COURSES_PROMISE, obj1);
        });

        it('should return currentCourseLoader', async () => {
            const obj1 = {};
            state.currentCourseLoader = obj1;

            await expect(store.actions.loadCourses(context)).resolves.toBe(obj1);

            expect(mockDispatch).not.toBeCalled();
            expect(mockCommit).not.toBeCalled();
        });
    });

    describe('update course', () => {
        it('should simply work', () => {
            const obj1 = {};
            store.actions.updateCourse(context, obj1);

            expect(mockCommit).toBeCalledTimes(1);
            expect(mockCommit).toBeCalledWith(types.UPDATE_COURSE, obj1);
        });
    });

    describe('update assignment', () => {
        it('should simply work', () => {
            const obj1 = {};
            store.actions.updateAssignment(context, obj1);

            expect(mockCommit).toBeCalledTimes(1);
            expect(mockCommit).toBeCalledWith(types.UPDATE_ASSIGNMENT, obj1);
        });
    });

    describe('set rubric', () => {
        it('should work', () => {
            const rubric = {};
            const maxPoints = {};
            const assignmentId = {};
            const data = {
                other: {},
                rubric,
                maxPoints,
                assignmentId,
            };

            store.actions.setRubric(context, data);

            expect(mockCommit).toBeCalledTimes(1);
            expect(mockCommit).toBeCalledWith(types.UPDATE_ASSIGNMENT, {
                assignmentId,
                assignmentProps: {
                    rubric,
                    fixed_max_rubric_points: maxPoints,
                },
            });
        });
    });

    describe('force force rubric', () => {
        it('should work when api succeeds', async () => {
            const single1 = {};
            const single2 = {};
            mockAxiosGet.mockClear();
            mockAxiosGet.mockReturnValueOnce(Promise.resolve({data: single2}));

            await store.actions.forceLoadRubric(context, single2);

            expect(axios.get).toBeCalledTimes(1);
            expect(axios.get).toBeCalledWith(`/api/v1/assignments/${single2}/rubrics/`);
            expect(mockCommit).toBeCalledTimes(1);
            expect(mockCommit).toBeCalledWith(types.UPDATE_ASSIGNMENT, {
                assignmentId: single2,
                assignmentProps: {
                    rubric: single2,
                },
            });
        });

        it('should clear when api fails', async () => {
            const single1 = {};
            const single2 = {};
            mockAxiosGet.mockClear();
            mockAxiosGet.mockReturnValueOnce(Promise.reject({data: single2}));

            await store.actions.forceLoadRubric(context, single2);

            expect(axios.get).toBeCalledTimes(1);
            expect(axios.get).toBeCalledWith(`/api/v1/assignments/${single2}/rubrics/`);
            expect(mockCommit).toBeCalledTimes(1);
            expect(mockCommit).toBeCalledWith(types.UPDATE_ASSIGNMENT, {
                assignmentId: single2,
                assignmentProps: {
                    rubric: null,
                },
            });
        });
    });
});
