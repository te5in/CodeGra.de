import moment from 'moment';

import { store } from '@/store';
import * as utils from '@/utils';
import * as assignmentState from '@/store/assignment-states';

const SERVER_PROPS = new Set([
    'id',
    'state',
    'description',
    'name',
    'is_lti',
    'cgignore',
    'cgignore_version',
    'whitespace_linter',
    'done_type',
    'done_email',
    'fixed_max_rubric_points',
    'max_grade',
    'group_set',
    'division_parent_id',
    'auto_test_id',
    'files_upload_enabled',
    'webhook_upload_enabled',
    'max_submissions',
    'amount_in_cool_off_period',
    'lms_name',
    'analytics_workspace_ids',
]);

const ALLOWED_UPDATE_PROPS = new Set([
    'state',
    'description',
    'name',
    'is_lti',
    'cgignore',
    'cgignore_version',
    'whitespace_linter',
    'done_type',
    'done_email',
    'fixed_max_rubric_points',
    'max_grade',
    'group_set',
    'division_parent_id',
    'auto_test_id',
    'files_upload_enabled',
    'webhook_upload_enabled',
    'max_submissions',
    'amount_in_cool_off_period',

    // Special properties that also may be set.
    'reminderTime',
    'deadline',
    'graders',
    'rubric',
    'cool_off_period',
]);

// eslint-disable-next-line
export class Assignment {
    constructor(props) {
        Object.assign(this, props);
        Object.freeze(this);
    }

    static fromServerData(serverData, courseId, canManage) {
        const props = {};
        SERVER_PROPS.forEach(prop => {
            props[prop] = serverData[prop];
        });

        props.courseId = courseId;
        props.canManage = canManage;

        props.deadline = moment.utc(serverData.deadline, moment.ISO_8601);
        props.createdAt = moment.utc(serverData.created_at, moment.ISO_8601);
        props.reminderTime = moment.utc(serverData.reminder_time, moment.ISO_8601);

        props.coolOffPeriod = moment.duration(serverData.cool_off_period, 'seconds');

        return new Assignment(props);
    }

    get course() {
        return store.getters['courses/courses'][this.courseId];
    }

    getReminderTimeOrDefault() {
        if (this.reminderTime.isValid()) {
            return this.reminderTime.clone();
        }

        const deadline = this.deadline;
        let baseTime = deadline;
        const now = moment();

        if ((deadline.isValid() && deadline.isBefore(now)) || !deadline.isValid()) {
            baseTime = now;
        }

        return baseTime.clone().add(1, 'weeks');
    }

    get hasDeadline() {
        return this.deadline.isValid();
    }

    // eslint-disable-next-line
    get created_at() {
        return utils.formatDate(this.createdAt);
    }

    getDeadlineAsString() {
        if (this.hasDeadline) {
            return utils.formatDate(this.deadline);
        }
        return null;
    }

    // eslint-disable-next-line
    getFormattedDeadline() {
        if (this.hasDeadline) {
            return utils.readableFormatDate(this.deadline);
        }
        return null;
    }

    getFormattedCreatedAt() {
        return utils.readableFormatDate(this.createdAt);
    }

    deadlinePassed(now = moment(), dflt = false) {
        if (this.deadline == null) {
            return dflt;
        }
        return now.isAfter(this.deadline);
    }

    canUploadWork(now = moment()) {
        const perms = this.course.permissions;

        if (!(perms.can_submit_own_work || perms.can_submit_others_work)) {
            return false;
        } else if (this.state === assignmentState.HIDDEN) {
            return false;
        } else if (!perms.can_upload_after_deadline && this.deadlinePassed(now)) {
            return false;
        } else {
            return true;
        }
    }

    get graders() {
        if (this.graderIds == null) {
            return null;
        }
        return this.graderIds.map(store.getters['users/getUser']);
    }

    _canSeeFeedbackType(type) {
        if (this.state === assignmentState.DONE) {
            return true;
        }
        const perm = {
            grade: 'can_see_grade_before_open',
            linter: 'can_see_linter_feedback_before_done',
            user: 'can_see_user_feedback_before_done',
        }[type];

        if (perm == null) {
            throw new Error(`Requested feedback type "${type}" is not known.`);
        }

        return utils.getProps(this.course, false, 'permissions', perm);
    }

    canSeeGrade() {
        return this._canSeeFeedbackType('grade');
    }

    canSeeUserFeedback() {
        return this._canSeeFeedbackType('user');
    }

    canSeeLinterFeedback() {
        return this._canSeeFeedbackType('linter');
    }

    get rubric() {
        return store.getters['rubrics/rubrics'][this.id];
    }

    update(newProps) {
        return new Assignment(
            Object.assign(
                {},
                this,
                Object.entries(newProps).reduce((acc, [key, value]) => {
                    if (!ALLOWED_UPDATE_PROPS.has(key)) {
                        throw TypeError(`Cannot set assignment property: ${key} to ${value}`);
                    } else if (key === 'graders') {
                        if (value == null) {
                            acc.graderIds = null;
                        } else {
                            value.forEach(grader =>
                                store.dispatch(
                                    'users/addOrUpdateUser',
                                    {
                                        user: grader,
                                    },
                                    { root: true },
                                ),
                            );
                            acc.graderIds = value.map(g => g.id);
                        }
                    } else if (key === 'deadline' || key === 'reminderTime') {
                        if (!moment.isMoment(value)) {
                            throw new Error(`${key} can only be set as moment`);
                        }
                        acc[key] = value;
                    } else if (key === 'cool_off_period') {
                        acc.coolOffPeriod = moment.duration(value, 'seconds');
                    } else {
                        acc[key] = value;
                    }

                    return acc;
                }, {}),
            ),
        );
    }
}
