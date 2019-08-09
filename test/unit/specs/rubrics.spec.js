import { mutations } from '@/store/modules/rubrics';
import { Rubric, RubricResult } from '@/models/rubric.js';

describe('The rubric store', () => {
    let state;
    let assignmentId;
    let submissionId;
    let mockRubric;
    let mockResult;

    beforeEach(() => {
        state = {
            rubrics: {},
            results: {},
        };
        assignmentId = 1;
        submissionId = 1;
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
        mockResult = {
            selected: [{ id: 1, points: 1 }],
        };

    });

    describe('mutations', () => {
        describe('setRubric', () => {
            it('should store null if null is passed', () => {
                mutations.setRubric(state, {
                    assignmentId,
                    rubric: null,
                });

                expect(state.rubrics[assignmentId]).toBeNull();
            });

            it('should store a new Rubric model', () => {
                mutations.setRubric(state, {
                    assignmentId,
                    rubric: mockRubric,
                });

                expect(state.rubrics[assignmentId]).toBeInstanceOf(Rubric);
            });

            it('should calculate the max number of points in the rubric', () => {
                mutations.setRubric(state, {
                    assignmentId,
                    rubric: [],
                });

                expect(state.rubrics[assignmentId].maxPoints).toBe(0);

                mutations.setRubric(state, {
                    assignmentId,
                    rubric: mockRubric,
                });

                expect(state.rubrics[assignmentId].maxPoints).toBe(18);
            });
        });

        describe('setResult', () => {
            it('should store a new RubricResult model', () => {
                mutations.setResult(state, {
                    submissionId,
                    result: mockResult,
                });

                const result = state.results[submissionId];

                expect(result).toBeInstanceOf(RubricResult);
                expect(result.selected.length).toBe(mockResult.selected.length);
                expect(result.points).toBe(1);
            });

            it('should store null as points if no items are selected', () => {
                mutations.setResult(state, {
                    submissionId,
                    result: Object.assign(mockResult, {
                        selected: [],
                    }),
                });

                const result = state.results[submissionId];

                expect(result).toBeInstanceOf(RubricResult);
                expect(result.selected.length).toBe(0);
                expect(result.points).toBeNull();
            });
        });

        describe('clearResult', () => {
            it('should delete the rubric from the store', () => {
                state.results[submissionId] = {};

                mutations.clearResult(state, { submissionId });

                expect(state.results[submissionId]).toBeUndefined();
            });
        });

        describe('setSelected', () => {
            it('should entirely replace the old selected value', () => {
                mutations.setResult(state, {
                    submissionId,
                    result: mockResult,
                });

                const result = state.results[submissionId];

                mutations.setSelected(state, {
                    result,
                    selected: [{ id: 0, points: 0 }],
                });

                expect(result.selected).toEqual([{ id: 0, points: 0 }]);
            });

            it('should update the points of the result', () => {
                mutations.setResult(state, {
                    submissionId,
                    result: mockResult,
                });

                const result = state.results[submissionId];

                expect(result.points).toBe(1);

                mutations.setSelected(state, {
                    result,
                    selected: [{ id: 0, points: 0 }],
                });

                expect(result.points).toBe(0);

                mutations.setSelected(state, {
                    result,
                    selected: [
                        { id: 0, points: 0 },
                        { id: 1, points: 1 },
                        { id: 2, points: 2 },
                    ],
                });

                expect(result.points).toBe(3);

                mutations.setSelected(state, {
                    result,
                    selected: [],
                });

                expect(result.points).toBeNull();
            });
        });

        describe('selectItem', () => {
            it('should update the points', () => {
                mutations.setResult(state, {
                    submissionId,
                    result: mockResult,
                });

                const result = state.results[submissionId];
                const row = mockRubric[1];
                const item = row.items[1];

                mutations.selectItem(state, { result, row, item });

                expect(result.selected.length).toBe(2);
                expect(result.selected).toContainEqual(item);
                expect(result.points).toBe(9);
            });

            it('should remove selected items from the same row', () => {
                mutations.setResult(state, {
                    submissionId,
                    result: mockResult,
                });

                const result = state.results[submissionId];
                const row = mockRubric[0];
                const item = row.items[0];

                mutations.selectItem(state, { result, row, item });

                expect(result.selected.length).toBe(1);
                expect(result.selected).toContainEqual(item);
                expect(result.points).toBe(0);
            });
        });

        describe('unselectItem', () => {
            it('should throw an error when item is not selected', () => {
                mutations.setResult(state, {
                    submissionId,
                    result: mockResult,
                });

                const result = state.results[submissionId];
                const row = mockRubric[1];
                const item = row.items[0];

                expect(() => {
                    mutations.unselectItem(state, { result, row, item });
                }).toThrow(ReferenceError);
            });

            it('should update the points', () => {
                mutations.setResult(state, {
                    submissionId,
                    result: mockResult,
                });

                const result = state.results[submissionId];
                let row = mockRubric[1];
                let item = row.items[0];

                mutations.selectItem(state, { result, row, item });

                mutations.unselectItem(state, { result, row, item });

                expect(result.selected.length).toBe(1);
                expect(result.selected).toEqual([{ id: 1, points: 1 }]);
                expect(result.points).toBe(1);

                row = mockRubric[0];
                item = mockRubric[1];

                mutations.unselectItem(state, { result, row, item });

                expect(result.selected.length).toBe(0);
                expect(result.selected).toEqual([]);
                expect(result.points).toBeNull();
            });
        });
    });
});
