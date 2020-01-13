// We first need to import the main store, to prevent undefined errors.
import { store } from '@/store';

import { actions } from '@/store/modules/courses';

import * as types from '@/store/mutation-types';
import * as utils from '@/utils';
import Vuex from 'vuex';
import Vue from 'vue';
import { Rubric } from '@/models/rubric';
import { Assignment } from '@/models/assignment';
import axios from 'axios';

function makeAssig(data, course, canManage) {
    return Assignment.fromServerData(data, course.id, canManage);
}

const initialCourses = [
    {
        assignments: [{
            id: 2,
            name: '2',
            fixed_max_rubric_points: null,
        }, {
            id: 3,
            name: '3',
            fixed_max_rubric_points: null,
        }],
        name: 'hello',
        id: 1,
    }, {
        assignments: [{
            id: 5,
            name: '5',
            fixed_max_rubric_points: null,
        }],
        name: 'bye',
        id: 4,
    },
];

function setInitialState() {
    store.commit(`courses/${types.SET_COURSES}`, [
        utils.deepCopy(initialCourses),
        { },
        { },
        { },
        { },
    ]);
};

const mockFormatGrade = jest.fn();
const mockAxiosGet = jest.fn();
axios.get = mockAxiosGet;

utils.formatGrade = mockFormatGrade;

describe('getters', () => {
    let state;

    beforeEach(() => {
        setInitialState();
    });

    describe('courses', () => {
        it('should return the state object', () => {
            expect(
                Object.values(store.getters['courses/courses']).sort((a, b) => a.id - b.id),
            ).toMatchObject(initialCourses);
        });
    });

    describe('assignments', () => {
        it('should work without courses', () => {
            store.commit(`courses/${types.SET_COURSES}`, [
                [],
                { },
                { },
                { },
                { },
            ]);
            expect(store.getters['courses/assignments']).toEqual({});
        });

        it('should work with courses', () => {
            const assigs = store.getters['courses/assignments'];
            expect(assigs).toMatchObject({
                2: {
                    id: 2,
                    name: '2',
                    fixed_max_rubric_points: null,
                    course: {
                        id: 1,
                    }
                },
                3: {
                    id: 3,
                    name: '3',
                    fixed_max_rubric_points: null,
                    course: {
                        id: 1,
                    }
                },
                5: {
                    id: 5,
                    name: '5',
                    fixed_max_rubric_points: null,
                    course: {
                        id: 4,
                    }
                },
            });
            expect(Object.values(assigs).every(x => x instanceof Assignment)).toBe(true);
        });
    });
});

describe('mutations', () => {
    beforeEach(() => {
        setInitialState();
    })

    describe('clear courses', () => {
        it('should clear all the things', () => {
            store.commit(`courses/${types.CLEAR_COURSES}`);
            expect(store.getters['courses/courses']).toEqual({});
            expect(store._modulesNamespaceMap['courses/'].state).toEqual({
                courses: {},
                currentCourseLoader: null,
            });
        });
    });

    describe('update course', () => {
        function getCourse(courseId) {
            return store.getters['courses/courses'][courseId];
        }

        it('should not work for id', () => {
            expect(
                () => store.commit(`courses/${types.UPDATE_COURSE}`,
                    { courseId: 1, courseProps: { id: 5 }},
                ),
            ).toThrow();
        });

        it('should not work for new props', () => {
            expect(
                () => store.commit(`courses/${types.UPDATE_COURSE}`,
                    { courseId: 1, courseProps: { newProp: 5 }},
                ),
            ).toThrow();
        });

        it('should not work for unknown courses', () => {
            expect(
                () => store.commit(`courses/${types.UPDATE_COURSE}`,
                    { courseId: 'UNKOWN', courseProps: { name: 5 }},
                ),
            ).toThrow();
        });

        it('should work for known props', () => {
            store.commit(`courses/${types.UPDATE_COURSE}`,
                { courseId: 1, courseProps: { name: 5 }},
            );
            expect(getCourse(1).name).toBe(5);
            expect(getCourse(4).name).toBe('bye');
        });
    });


    describe('update assignment', () => {
        function getAssig(assigId) {
            return store.getters['courses/assignments'][assigId];
        }

        it('should not work for id', () => {
            expect(
                () => store.commit(`courses/${types.UPDATE_ASSIGNMENT}`,
                    { assignmentId: 2, assignmentProps: { id: 5 }},
                ),
            ).toThrow();
        });

        it('should not work for new props', () => {
            expect(
                () => store.commit(`courses/${types.UPDATE_ASSIGNMENT}`,
                    { assignmentId: 2, assignmentProps: { newProp: 5 }},
                ),
            ).toThrow();

            expect(
                () => store.commit(`courses/${types.UPDATE_ASSIGNMENT}`,
                    { assignmentId: 2, assignmentProps: { submission: 5 }},
                ),
            ).toThrow();
        });

        it('should work for some unknown props', () => {
            ['auto_test_id'].forEach((key) => {
                const obj1 = {};

                store.commit(`courses/${types.UPDATE_ASSIGNMENT}`,
                    { assignmentId: 2, assignmentProps: { [key]: obj1 }},
                );

                expect(getAssig(2)[key]).toBe(obj1);
                expect(getAssig(3)[key]).not.toBe(obj1);
            });
        });


        it('should not work for unknown assignments', () => {
            expect(
                () => store.commit(`courses/${types.UPDATE_ASSIGNMENT}`,
                    { courseId: 'UNKOWN', assignmentProps: { name: 5 }},
                ),
            ).toThrow();
        });

        it('should work for known props', () => {
            store.commit(`courses/${types.UPDATE_ASSIGNMENT}`,
                { assignmentId: 2, assignmentProps: { name: 5 }},
            );
            expect(getAssig(2).name).toBe(5);
            expect(getAssig(3).name).toBe('3');
        });
    });

    describe('set course promise', () => {
        it('should set the state prop', () => {
            const obj1 = {};
            store.commit(`courses/${types.SET_COURSES_PROMISE}`, obj1);
            expect(store._modulesNamespaceMap['courses/'].state.currentCourseLoader).toBe(obj1);
        });
    });

});

describe('actions', () => {
    let mockDispatch;
    let mockCommit;
    let mockRubric;
    let context;

    beforeEach(() => {
        setInitialState()
        mockDispatch = jest.fn();
        mockCommit = jest.fn();
        context = {
            dispatch: mockDispatch,
            commit: mockCommit,
            state: {
                currentCourseLoader: null,
                courses: {},
            },
        };
        mockRubric = [
            {
                id: 0,
                items: [
                    { id: 0, points: 0 },
                    { id: 1, points: 1 },
                    { id: 2, points: 2 },
                ],
            },
            {
                id: 1,
                items: [
                    { id: 3, points: 4 },
                    { id: 4, points: 8 },
                    { id: 5, points: 16 },
                ],
            },
        ];
    });

    describe('load courses', () => {
        it('should reload courses', async () => {
            const obj1 = {};
            mockDispatch.mockReturnValueOnce(obj1);

            await actions.loadCourses(context);

            expect(mockDispatch).toBeCalledTimes(1);
            expect(mockDispatch).toBeCalledWith('reloadCourses');
            expect(mockCommit).toBeCalledTimes(1);
            expect(mockCommit).toBeCalledWith(types.SET_COURSES_PROMISE, obj1);
        });

        it('should return currentCourseLoader', async () => {
            const obj1 = {};
            store.commit(`courses/${types.SET_COURSES_PROMISE}`, obj1);

            await expect(store.dispatch('courses/loadCourses')).resolves.toBe(obj1);

            expect(mockDispatch).not.toBeCalled();
            expect(mockCommit).not.toBeCalled();
        });
    });

    describe('update course', () => {
        it('should simply work', async () => {
            const obj1 = {};
            await actions.updateCourse(context, obj1);

            expect(mockCommit).toBeCalledTimes(1);
            expect(mockCommit).toBeCalledWith(types.UPDATE_COURSE, obj1);
        });
    });

    describe('update assignment', () => {
        it('should simply work', async () => {
            const obj1 = {};
            await actions.updateAssignment(context, obj1);

            expect(mockCommit).toBeCalledTimes(1);
            expect(mockCommit).toBeCalledWith(types.UPDATE_ASSIGNMENT, obj1);
        });
    });

    describe('setRubric', () => {
        beforeEach(() => {
            store.commit(`courses/${types.SET_COURSES_PROMISE}`, {});
        });

        let assignmentId = 5;
        function getAssig(assignmentId) {
            return store.getters['courses/assignments'][`${assignmentId}`];
        }

        it('should store null if null is passed', async () => {
            await store.dispatch('courses/setRubric', {
                assignmentId,
                rubric: null,
                maxPoints: null,
            });

            expect(getAssig(assignmentId).rubric).toBeNull();
        });

        it('should store a new Rubric model', async () => {
            await store.dispatch('courses/setRubric', {
                assignmentId,
                rubric: mockRubric,
            });

            expect(getAssig(assignmentId).rubricModel).toBeInstanceOf(Rubric);
        });

        it('should calculate the max number of points in the rubric', async () => {
            await store.dispatch('courses/setRubric', {
                assignmentId,
                rubric: [],
                maxPoints: null,
            });
            expect(getAssig(assignmentId).fixed_max_rubric_points).toBeNull();
            expect(getAssig(assignmentId).rubricModel.maxPoints).toBe(0);

            await store.dispatch('courses/setRubric', {
                assignmentId,
                rubric: mockRubric,
                maxPoints: null,
            });
            expect(getAssig(assignmentId).fixed_max_rubric_points).toBeNull();
            expect(getAssig(assignmentId).rubricModel.maxPoints).toBe(18);

            await store.dispatch('courses/setRubric', {
                assignmentId,
                rubric: mockRubric,
                maxPoints: 5,
            });
            expect(getAssig(assignmentId).fixed_max_rubric_points).toBe(5);
            expect(getAssig(assignmentId).rubricModel.maxPoints).toBe(5);

            await store.dispatch('courses/setRubric', {
                assignmentId,
                rubric: mockRubric,
                maxPoints: 0,
            });
            expect(getAssig(assignmentId).fixed_max_rubric_points).toBe(0);
            expect(getAssig(assignmentId).rubricModel.maxPoints).toBe(0);
        });

        it('should commit something', async () => {
            const rubric = mockRubric;
            const maxPoints = {};
            const assignmentId = {};
            const data = {
                other: {},
                rubric,
                maxPoints,
                assignmentId,
            };

            await actions.setRubric(context, data);

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

            await actions.forceLoadRubric(context, single2);

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

            await actions.forceLoadRubric(context, single2);

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
