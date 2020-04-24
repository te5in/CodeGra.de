// We first need to import the main store, to prevent undefined errors.
import { store } from '@/store';

import { actions } from '@/store/modules/courses';

import * as types from '@/store/mutation-types';
import * as utils from '@/utils';
import Vuex from 'vuex';
import Vue from 'vue';
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
        }, {
            id: 3,
            name: '3',
        }],
        name: 'hello',
        id: 1,
    }, {
        assignments: [{
            id: 5,
            name: '5',
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
                    course: {
                        id: 1,
                    }
                },
                3: {
                    id: 3,
                    name: '3',
                    course: {
                        id: 1,
                    }
                },
                5: {
                    id: 5,
                    name: '5',
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
    });

    describe('load courses', () => {
        it('should reload courses', async () => {
            const obj1 = {};
            mockDispatch.mockResolvedValueOnce(obj1);

            actions.loadCourses(context).then(() => {
                expect(mockDispatch).toBeCalledTimes(1);
                expect(mockDispatch).toBeCalledWith('reloadCourses');
                expect(mockCommit).toBeCalledTimes(1);
                expect(mockCommit).toBeCalledWith(types.SET_COURSES_PROMISE, obj1);
            });
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
            const obj1 = { assignmentId: 5, assignmentProps: {} };
            const obj2 = {};
            const obj3 = {};

            const res = await actions.updateAssignment(Object.assign({}, context, {
                getters: {
                    assignments: {
                        5: obj2,
                        6: obj3,
                    },
                },
            }), obj1);

            expect(mockCommit).toBeCalledTimes(1);
            expect(mockCommit).toBeCalledWith(types.UPDATE_ASSIGNMENT, obj1);
            // Should return the found assignment.
            expect(res).toBe(obj2);
        });
    });
});
