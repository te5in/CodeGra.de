import axios from 'axios';
import moment from 'moment';
import { nameOfUser, getNoNull } from '@/utils';

import { store } from '@/store';

export class Group {
    constructor(data) {
        // Make sure id can never be overridden, as this would break all code.
        Object.defineProperty(this, 'id', { value: data.id, enumerable: true });

        data.members.forEach(user => {
            store.dispatch('users/addOrUpdateUser', { user });
        });

        this.memberIds = data.members.map(m => m.id);
        this.name = data.name;
        this.groupSetId = data.group_set_id;
        this.createdAt = moment.utc(data.created_at);
    }

    get members() {
        return this.memberIds.map(store.getters['users/getUser']);
    }

    getMemberStates(assignmentId) {
        return axios.get(`/api/v1/assignments/${assignmentId}/groups/${this.id}/member_states/`);
    }
}

export class User {
    constructor(data, oldObject = null) {
        // Make sure id can never be overridden, as this would break all code.
        Object.defineProperty(this, 'id', { value: data.id, enumerable: true });
        this.name = getNoNull('name', data, oldObject);
        this.username = getNoNull('username', data, oldObject);
        this.is_test_student = getNoNull('is_test_student', data, oldObject);

        this.group = data.group && Object.freeze(new Group(data.group));

        this.readableName = nameOfUser(this);
        Object.freeze(this);
    }

    get isGroup() {
        return !!this.group;
    }

    get isTestStudent() {
        return !!this.is_test_student;
    }

    isMemberOf(group) {
        if (!group) {
            return false;
        }

        return group.memberIds.some(memberId => memberId === this.id);
    }

    getGroupMembers() {
        if (!this.isGroup) return [];
        return this.group.members;
    }
}
