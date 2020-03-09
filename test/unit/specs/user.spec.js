/* SPDX-License-Identifier: AGPL-3.0-only */
import { User } from '@/models';

describe('User model', () => {
    const u1 = new User({'id': 1, 'name': 'Piet', 'username': 'pietie', 'group': null, 'is_test_student': false});
    const u1_copy = new User({'id': 1, 'name': 'Piet', 'username': 'pietie', 'group': null, 'is_test_student': false});
    const u2 = new User({'id': 2, 'name': 'Piet', 'username': 'pietie', 'group': null, 'is_test_student': false});
    const g1 = new User({'id': 3, 'name': 'Piet', 'username': 'pietie', 'group': {
        'members': [{'id': 1}],
        'name': 'MY NAME',
        'created_at': '2020-02-17T12:34:27+00:00',
        'group_set_id': 1,
    }, 'is_test_student': false});

    it('should be possible to compare two users', () => {
        expect(u1.isEqualOrMemberOf(u1_copy)).toBe(true);
        expect(u1_copy.isEqualOrMemberOf(u1)).toBe(true);

        expect(u1.isEqualOrMemberOf(u2)).toBe(false);

        expect(u1.isEqualOrMemberOf(g1)).toBe(true);
        expect(g1.isEqualOrMemberOf(g1)).toBe(true);
        expect(g1.isEqualOrMemberOf(u1)).toBe(true);
        expect(u2.isEqualOrMemberOf(g1)).toBe(false);
    });

    it('should be possible to update a user', () => {
        expect(u1.name).toBe('Piet');
        expect(new User({'name': 'JAN'}, u1).name).toBe('JAN');
        expect(u1.name).toBe('Piet');
    });

    it('should not be possible to change an attribute', () => {
        expect(() => { u1.name = 'NEW' }).toThrow();
        expect(u1.name).toBe('Piet');
    });

    it('should have an attribute indicating if it is a group', () => {
        expect(u1.isGroup).toBe(false);
        expect(g1.isGroup).toBe(true);
    });

    it('should have an attribute indicating if it is a test student', () => {
        expect(u1.isTestStudent).toBe(false);
        expect(new User({'is_test_student': null}, u1).isTestStudent).toBe(false);
        expect(new User({'is_test_student': 'THIS WILL BECOME A BOOL'}, u1).isTestStudent).toBe(true);
        expect(u1.isTestStudent).toBe(false);
    });

    it('should be possible to get the members of a group', () => {
        expect(u1.getGroupMembers()).toEqual([]);

        expect(g1.getGroupMembers().map(x => x.id)).toEqual([u1.id]);
    });
});
