/* SPDX-License-Identifier: AGPL-3.0-only */
import Submission from '@/pages/Submission';
import { shallowMount, createLocalVue } from '@vue/test-utils';
import VueRouter from 'vue-router';
import Vuex from 'vuex';
import BootstrapVue from 'bootstrap-vue';

jest.mock('axios');

const localVue = createLocalVue();

localVue.use(Vuex);
localVue.use(BootstrapVue);

const router = new VueRouter();

function jsonCopy(src) {
    return JSON.parse(JSON.stringify(src));
}

describe('Submission.vue', () => {
    let store;
    let courses;
    let submissions;
    let mockLoadSubs;
    let wrapper;
    let comp;
    let tree1;
    let tree2;
    let tree3;
    let tree4;
    let $route;
    let $router;
    let mockGet;
    let rubric = {};

    beforeEach(() => {
        tree1 = {
            name: 'root1',
            id: 1,
            entries: [
                {
                    name: 'file1',
                    id: 2,
                },
                {
                    name: 'sub1',
                    id: 3,
                    entries: [{ name: 'file2', id: 4 }],
                },
            ],
        };


        tree2 = jsonCopy(tree1);
        tree2.entries.splice(0, 1);
        tree2.entries[0].entries[0].id = 5;
        tree2.entries[0].entries.push({ name: 'file3', id: 6 });

        tree3 = jsonCopy(tree1);
        tree3.entries.push({
            name: 'sub2',
            id: 4,
            entries: [{
                name: 'file4',
                id: 7,
            }],
        });

        tree4 = jsonCopy(tree1);
        tree4.entries.splice(1, 1);
        tree4.entries.push({
            name: 'sub1',
            id: 8,
        });

        const user = {id: 1000};
        submissions = [{id: 1, user}, {id: 2, user}, {id: 3, user}, {id: 4, user}];
        courses = {
            1: {
                assignments: [{
                    id: 2,
                    submissions,
                }],
                is_lti: false,
            },
        };
        courses[1].assignments.forEach(assig => { assig.course = courses[1]; });

        mockLoadSubs = jest.fn(() => Promise.resolve(true));

        store = new Vuex.Store({
            modules: {
                courses: {
                    state: {
                        courses,
                    },
                    getters: {
                        courses: () => courses,
                        assignments: () => ({ 2: courses[1].assignments[0] }),
                    },
                    actions: {
                        loadSubmissions: mockLoadSubs,
                    },
                    namespaced: true,
                },
                user: {
                    getters: {
                        id: () => -1,
                    },
                    namespaced: true,
                },
            },
        });

        $route = {
            query: {
            },
            params: {
                courseId: '1',
                assignmentId: '2',
                submissionId: '3',
            },
        };
        $router = {
            push: jest.fn(),
            replace: jest.fn(),
        };

        mockGet = jest.fn(async (path, opts) => new Promise((resolve) => {
            let res;
            if (/^.api.v1.submissions.[0-9]+.files./.test(path)) {
                if (opts && opts.params.owner === 'teacher') {
                    res = jsonCopy(tree2);
                } else {
                    res = jsonCopy(tree1);
                }
            } else if (/^.api.v1.submissions.[0-9]+.rubrics./.test(path)) {
                res = rubric;
            }
            resolve({ data: res });
        }));

        wrapper = shallowMount(Submission, {
            store,
            localVue,
            router,
            mocks: {
                $hasPermission(perms) {
                    if (Array.isArray(perms))
                        return perms.map(() => true)
                    else
                        return true;
                },
                $route,
                $router,
                $http: {
                    get: mockGet,
                },
            },
        });
        comp = wrapper.vm;
    });

    describe('Computed', () => {
        it('ids should be numbers or NaN', () => {
            expect(typeof comp.courseId).toBe('number');
            expect(typeof comp.assignmentId).toBe('number');
            expect(typeof comp.submissionId).toBe('number');
            expect(comp.courseId).toBe(1);
            expect(comp.assignmentId).toBe(2);
            expect(comp.submissionId).toBe(3);

            $route.params.assignmentId = 'hello';
            $route.params.courseId = 'hello';
            $route.params.submissionId = 'hello';

            expect(isNaN(comp.courseId)).toBe(true);
            expect(isNaN(comp.submissionId)).toBe(true);
            expect(isNaN(comp.assignmentId)).toBe(true);
        });

        it('objects should be retrieved from the store or default', () => {
            expect(comp.assignment).toBe(courses[1].assignments[0]);
            expect(comp.assignment.id).toBe(2);

            expect(comp.submissions).toBe(submissions);
            expect(comp.submission).toBe(submissions[2]);
            expect(comp.submission.id).toBe(3);

            $route.params.assignmentId = 'hello';
            $route.params.courseId = 'hello';
            $route.params.submissionId = 'hello';

            expect(comp.assignment).toBe(null);
            expect(comp.submissions).toEqual([]);
            expect(comp.submission).toBe(null);
        });

        it('booleans should be booleans', () => {
            expect(comp.diffMode).toBe(false);
            expect(comp.warnComment).toBe(false);
            expect(comp.overviewMode).toBe(false);

            comp.canSeeFeedback = false;
            expect(comp.overviewMode).toBe(false);

            comp.canSeeFeedback = true;
            comp.$set($route.query, 'overview', 0);
            expect(comp.overviewMode).toBe(true);
        });
    });

    describe('Watchers', () => {
        it('submission should be watched', async () => {
            await comp.$nextTick();
            for (let i = 0; i < 10 && comp.loadingInner; i++) {
                await comp.$nextTick();
            }
            expect(comp.loadingInner).toBe(false);

            comp.matchFiles = jest.fn(() => ({}));
            mockGet.mockClear();

            comp.$set($route.params, 'submissionId', 2);

            await comp.$nextTick();
            expect(comp.loadingInner).toBe(true);
            expect(comp.loadingPage).toBe(false);
            await comp.$nextTick();

            expect(mockGet).toBeCalledTimes(3);
            expect(mockGet).toBeCalledWith('/api/v1/submissions/2/files/');
            expect(mockGet).toBeCalledWith('/api/v1/submissions/2/files/', {params: {owner: 'teacher'}});
            expect(comp.studentTree.isStudent).toBe(true);
            expect(comp.studentTree).toMatchObject(tree1);

            expect(comp.teacherTree.isTeacher).toBe(true);
            expect(comp.teacherTree).toMatchObject(tree2);

            await comp.$nextTick();
            expect(comp.matchFiles).toBeCalledTimes(1);

            expect(mockGet).toBeCalledWith('/api/v1/submissions/2/rubrics/');
            expect(comp.rubric).toBe(rubric);

            expect(comp.loadingPage).toBe(false);
            // Wait max 10 ticks
            for (let i = 0; i < 10; i++) {
                if (!comp.loadingInner) {
                    break;
                }
                await comp.$nextTick();
            }
            expect(comp.loadingInner).toBe(false);
        });
    });

    describe('matchFiles', () => {
        it('should be a function', () => {
            expect(typeof comp.matchFiles).toBe('function');
        });

        it('should work with two identical trees', () => {
            expect(comp.matchFiles(tree1, tree1)).toEqual({
                name: 'root1',
                entries: [
                    {
                        name: 'file1',
                        ids: [2, 2],
                    },
                    {
                        name: 'sub1',
                        entries: [{ name: 'file2', ids: [4, 4] }],
                    },
                ],
            });

            // No revision should be added
            expect(tree1.entries[0].revision).toBe(undefined);
        });

        it('should work with a modified tree', () => {
            expect(comp.matchFiles(tree1, tree2)).toEqual({
                name: 'root1',
                entries: [
                    {
                        name: 'file1',
                        ids: [2, null],
                    },
                    {
                        name: 'sub1',
                        entries: [
                            { name: 'file2', ids: [4, 5] },
                            { name: 'file3', ids: [null, 6] },
                        ],
                    },
                ],
            });
            expect(tree1.entries[0]).toEqual({
                name: 'file1',
                id: 2,
                revision: null,
            });
            expect(tree1.entries[1]).toEqual({
                entries: [{ name: 'file2', id: 4, revision: expect.any(Object) }],
                name: 'sub1',
                id: 3,
            });
        });

        it('should work with a inserted directory', () => {
            expect(comp.matchFiles(tree1, tree3)).toEqual({
                name: 'root1',
                entries: [
                    {
                        name: 'file1',
                        ids: [2, 2],
                    },
                    {
                        name: 'sub1',
                        entries: [{ name: 'file2', ids: [4, 4] }],
                    },
                    {
                        name: 'sub2',
                        entries: [{ name: 'file4', ids: [null, 7] }],
                    },
                ],
            });
        });

        it('should work when replacing a directory with a file', () => {
            expect(comp.matchFiles(tree1, tree4)).toEqual({
                name: 'root1',
                entries: [
                    {
                        name: 'file1',
                        ids: [2, 2],
                    },
                    {
                        name: 'sub1',
                        entries: [{ name: 'file2', ids: [4, null] }],
                    },
                    {
                        name: 'sub1',
                        ids: [null, 8],
                    },
                ],
            });
            expect(tree1.entries[1]).toEqual({
                entries: expect.any(Array),
                name: 'sub1',
                revision: expect.any(Object),
                id: 3,
            });
        });

        it('should work when replacing a file with a directory', () => {
            expect(comp.matchFiles(tree4, tree1)).toEqual({
                name: 'root1',
                entries: [
                    {
                        name: 'file1',
                        ids: [2, 2],
                    },
                    {
                        name: 'sub1',
                        entries: [{ name: 'file2', ids: [null, 4] }],
                    },
                    {
                        name: 'sub1',
                        ids: [8, null],
                    },
                ],
            });
            expect(tree4.entries[1]).toEqual({
                name: 'sub1',
                revision: expect.any(Object),
                id: 8,
            });
        });
    });
});
