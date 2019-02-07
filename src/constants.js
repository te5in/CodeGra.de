/* SPDX-License-Identifier: AGPL-3.0-only */
export const MANAGE_ASSIGNMENT_PERMISSIONS = Object.freeze([
    'can_edit_assignment_info',
    'can_assign_graders',
    'can_edit_cgignore',
    'can_grade_work',
    'can_update_grader_status',
    'can_use_linter',
    'can_update_course_notifications',
    'manage_rubrics',
    'can_upload_bb_zip',
    'can_submit_others_work',
    'can_edit_maximum_grade',
    'can_view_plagiarism',
    'can_manage_plagiarism',
    'can_edit_group_assignment',
]);

export const MANAGE_GENERAL_COURSE_PERMISSIONS = Object.freeze([
    'can_edit_course_users',
    'can_edit_course_roles',
    'can_edit_group_set',
]);

export const MANAGE_COURSE_PERMISSIONS = Object.freeze([
    ...new Set([...MANAGE_ASSIGNMENT_PERMISSIONS, ...MANAGE_GENERAL_COURSE_PERMISSIONS]),
]);

export const MANAGE_SITE_PERIMSSIONS = Object.freeze(['can_manage_site_users']);
