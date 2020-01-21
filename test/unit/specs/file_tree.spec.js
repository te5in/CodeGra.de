import { FileTree } from '@/models/submission';
import * as utils from '@/utils';

describe('The submission file tree', () => {
    let mockStudentTree;
    let mockTeacherTree;
    let fileTree;

    beforeEach(() => {
        mockStudentTree = {
            id: 0,
            name: 'dir-0',
            entries: [
                {
                    id: 6,
                    name: '.hidden-file',
                },
                {
                    id: 1,
                    name: 'file-1',
                },
                {
                    id: 2,
                    name: 'file-2',
                },
                {
                    id: 3,
                    name: 'file-3',
                },
                {
                    id: 4,
                    name: 'dir-4',
                    entries: [],
                },
            ],
        };
        mockTeacherTree = {
            id: 0,
            name: 'dir-0',
            entries: [
                {
                    id: 5,
                    name: 'file-1',
                },
                {
                    id: 3,
                    name: 'file-3',
                },
                {
                    id: 4,
                    name: 'dir-4',
                    entries: [],
                },
            ],
        };
        fileTree = FileTree.fromServerData(mockStudentTree, mockTeacherTree);
    });

    describe('constructor', () => {
        it('should calculate the diff tree between the student and the teacher', () => {
            const diff = fileTree.diff;
            const entries = diff.entries;

            expect(diff).not.toBeNull();
            expect(entries.find(x => x.name === 'file-1').ids).toEqual([1, 5])
            expect(entries.find(x => x.name === 'file-2').ids).toEqual([2, null])
            expect(entries.find(x => x.name === 'file-3').ids).toEqual([3, 3])
        });

        it('should calculate a mapping between file id and name', () => {
            expect(fileTree.flattened).toBeDefined();
            expect(fileTree.flattened[1]).toBe('file-1');
            expect(fileTree.flattened[2]).toBe('file-2');
            expect(fileTree.flattened[5]).toBe('file-1');
        });

        it('should accept null for the teacher tree', () => {
            expect(() => {
                fileTree = FileTree.fromServerData(mockStudentTree, null);
            }).not.toThrow();
            expect(fileTree.teacher).toBe(null);

            for (let i = 0; i < fileTree.diff.entries.length; i++) {
                const e = fileTree.diff.entries[i];

                expect(e.ids[0]).toBe(e.ids[1]);
            }
        });
    });

    describe('hasRevision', () => {
        it('should return true if the given file has a revision', () => {
            const f1 = fileTree.student.entries.find(x => x.id === 1);
            const f2 = fileTree.student.entries.find(x => x.id === 2);

            expect(fileTree.hasRevision(f1)).toBeTruthy();
            expect(fileTree.hasRevision(f2)).toBeTruthy();
        });

        it('should return false if the given file has no revision', () => {
            const f3 = fileTree.student.entries.find(x => x.id === 3);
            expect(fileTree.hasRevision(f3)).toBeFalsy();
        });

        it('should return true if the given file is a directory and any of its children has a revision', () => {
            const f0 = fileTree.student;
            expect(fileTree.hasRevision(f0)).toBeTruthy();
        });

        it('should return false if the given file is a directory and none of its children has a revision', () => {
            const f4 = fileTree.student.entries.find(x => x.id === 4);;
            expect(fileTree.hasRevision(f4)).toBeFalsy();
        });
    });

    describe('findFirstFile', () => {
        it('should not return a directory', () => {
            expect(fileTree.getFirstFile('student')).not.toHaveProperty('entries');
            expect(fileTree.getFirstFile('teacher')).not.toHaveProperty('entries');
            expect(fileTree.getFirstFile('diff')).not.toHaveProperty('entries');
        });

        it('should not return a hidden file starting with "."', () => {
            expect(fileTree.getFirstFile('student').name).not.toMatch(/^\./);
        });
    });

    describe('search', () => {
        it('should not be able to find the top level directory', () => {
            expect(fileTree.search('student', 0)).toBeNull();
            expect(fileTree.search('teacher', 0)).toBeNull();
            expect(fileTree.search('diff', 0)).toBeNull();
        });

        it('should find the item with the requested id if it is in the tree', () => {
            const f1 = fileTree.search('student', 1);
            const f2 = fileTree.search('student', 2);
            const f3 = fileTree.search('teacher', 3);

            expect(f1.id).toBe(1);
            expect(f2.id).toBe(2);
            expect(f3.id).toBe(3);
        });

        it('should find the item whose revision\'s id is equal to the requested id', () => {
            // The revision of file with id 5 has id 1
            const f1 = fileTree.search('student', 5);
            expect(f1.id).toBe(1);

            const d1 = fileTree.search('diff', 1);
            const d5 = fileTree.search('diff', 5);
            expect(d1.ids).toEqual([1, 5]);
            expect(d5.ids).toEqual([1, 5]);
        });
    });

    describe('matchFiles', () => {
        let tree1;
        let tree2;
        let tree3;
        let tree4;

        function jsonCopy(src) {
            return JSON.parse(JSON.stringify(src));
        }

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
        });

        it('should work with two identical trees', () => {
            const fileTree = FileTree.fromServerData(tree1, tree1);

            expect(fileTree.diff).toEqual({
                name: 'root1',
                ids: [1, 1],
                entries: [
                    {
                        name: 'file1',
                        ids: [2, 2],
                    },
                    {
                        name: 'sub1',
                        entries: [{ name: 'file2', ids: [4, 4] }],
                        ids: [3, 3]
                    },
                ],
            });

            // No revision should be added
            expect(fileTree.hasRevision(fileTree.student.entries[0])).toBe(false);
        });

        it('should work with a modified tree', () => {
            const fileTree = FileTree.fromServerData(tree1, tree2);

            expect(fileTree.diff).toEqual({
                name: 'root1',
                ids: [1, 1],
                entries: [
                    {
                        name: 'file1',
                        ids: [2, null],
                    },
                    {
                        name: 'sub1',
                        ids: [3, 3],
                        entries: [
                            { name: 'file2', ids: [4, 5] },
                            { name: 'file3', ids: [null, 6] },
                        ],
                    },
                ],
            });
            expect(fileTree.hasRevision(tree1.entries[0])).toBe(true);
            expect(fileTree.getRevisionId(tree1.entries[0])).toBe(null);
        });

        it('should work with a inserted directory', () => {
            const fileTree = FileTree.fromServerData(tree1, tree3);

            expect(fileTree.diff).toEqual({
                name: 'root1',
                ids: [1, 1],
                entries: [
                    {
                        name: 'file1',
                        ids: [2, 2],
                    },
                    {
                        name: 'sub1',
                        ids: [3, 3],
                        entries: [{ name: 'file2', ids: [4, 4] }],
                    },
                    {
                        name: 'sub2',
                        ids: [null, 4],
                        entries: [{ name: 'file4', ids: [null, 7] }],
                    },
                ],
            });
        });

        it('should work when replacing a directory with a file', () => {
            const fileTree = FileTree.fromServerData(tree1, tree4);

            expect(fileTree.diff).toEqual({
                name: 'root1',
                ids: [1, 1],
                entries: [
                    {
                        name: 'file1',
                        ids: [2, 2],
                    },
                    {
                        name: 'sub1',
                        ids: [3, null],
                        entries: [{ name: 'file2', ids: [4, null] }],
                    },
                    {
                        name: 'sub1',
                        ids: [null, 8],
                    },
                ],
            });
            expect(fileTree.hasRevision(tree1.entries[1])).toBe(true);
        });

        it('should work when replacing a file with a directory', () => {
            const fileTree = FileTree.fromServerData(tree4, tree1);

            expect(fileTree.diff).toEqual({
                name: 'root1',
                ids: [1, 1],
                entries: [
                    {
                        name: 'file1',
                        ids: [2, 2],
                    },
                    {
                        name: 'sub1',
                        ids: [null, 3],
                        entries: [{ name: 'file2', ids: [null, 4] }],
                    },
                    {
                        name: 'sub1',
                        ids: [8, null],
                    },
                ],
            });
            expect(fileTree.hasRevision(tree4.entries[1])).toBe(true);
            expect(fileTree.hasRevision(tree1.entries[1])).toBe(true);

            // They don't have a equivalent, as they are of different types.
            expect(fileTree.getRevisionId(tree4.entries[1])).toBe(null);
            expect(fileTree.getRevisionId(tree1.entries[1])).toBe(null);
        });
    });
});
