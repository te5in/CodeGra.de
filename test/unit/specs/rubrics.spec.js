import { mutations } from '@/store/modules/rubrics';
import { RubricResult } from '@/models/rubric.js';

describe('The rubric store', () => {
    let state;
    let assignmentId;
    let submissionId;
    let mockRubric;
    let mockResult;

    function getResult() {
        return state.results[submissionId];
    }

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

                expect(getResult()).toBeUndefined();
            });
        });

        describe('setSelected', () => {
            it('should entirely replace the old selected value', () => {
                mutations.setResult(state, {
                    submissionId,
                    result: mockResult,
                    submissionId,
                });

                mutations.setSelected(state, {
                    result: getResult(),
                    selected: [{ id: 0, points: 0 }],
                    submissionId,
                });

                expect(getResult().selected).toEqual([{ id: 0, points: 0 }]);
            });

            it('should update the points of the result', () => {
                mutations.setResult(state, {
                    submissionId,
                    result: mockResult,
                });

                expect(getResult().points).toBe(1);

                mutations.setSelected(state, {
                    result: getResult(),
                    selected: [{ id: 0, points: 0 }],
                    submissionId,
                });

                expect(getResult().points).toBe(0);

                mutations.setSelected(state, {
                    result: getResult(),
                    selected: [
                        { id: 0, points: 0 },
                        { id: 1, points: 1 },
                        { id: 2, points: 2 },
                    ],
                    submissionId,
                });

                expect(getResult().points).toBe(3);

                mutations.setSelected(state, {
                    result: getResult(),
                    selected: [],
                    submissionId,
                });

                expect(getResult().points).toBeNull();
            });
        });

        describe('selectItem', () => {
            it('should update the points', () => {
                mutations.setResult(state, {
                    submissionId,
                    result: mockResult,
                });

                const row = mockRubric[1];
                const item = row.items[1];

                mutations.selectItem(state, { result: getResult(), row, item, submissionId });

                expect(getResult().selected.length).toBe(2);
                expect(getResult().selected).toContainEqual(item);
                expect(getResult().points).toBe(9);
            });

            it('should remove selected items from the same row', () => {
                mutations.setResult(state, {
                    submissionId,
                    result: mockResult,
                });

                const row = mockRubric[0];
                const item = row.items[0];

                mutations.selectItem(state, { result: getResult(), row, item, submissionId });

                expect(getResult().selected.length).toBe(1);
                expect(getResult().selected).toContainEqual(item);
                expect(getResult().points).toBe(0);
            });
        });

        describe('unselectItem', () => {
            it('should throw an error when item is not selected', () => {
                mutations.setResult(state, {
                    submissionId,
                    result: mockResult,
                });

                const row = mockRubric[1];
                const item = row.items[0];

                expect(() => {
                    mutations.unselectItem(state, { result: getResult(), row, item, submissionId });
                }).toThrow(ReferenceError);
            });

            it('should update the points', () => {
                mutations.setResult(state, {
                    submissionId,
                    result: mockResult,
                });

                let row = mockRubric[1];
                let item = row.items[0];

                mutations.selectItem(state, { result: getResult(), row, item, submissionId });

                mutations.unselectItem(state, { result: getResult(), row, item, submissionId });

                expect(getResult().selected.length).toBe(1);
                expect(getResult().selected).toEqual([{ id: 1, points: 1 }]);
                expect(getResult().points).toBe(1);

                row = mockRubric[0];
                item = mockRubric[1];

                mutations.unselectItem(state, { result: getResult(), row, item, submissionId });

                expect(getResult().selected.length).toBe(0);
                expect(getResult().selected).toEqual([]);
                expect(getResult().points).toBeNull();
            });
        });
    });
});
