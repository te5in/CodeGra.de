from psef.lti.v1_3.roles import IMS_LIS, SystemRole, ContextRole


def test_context_roles(describe):
    with describe('Roles should be parsed in order'):
        r1, r2 = ContextRole.parse_roles([
            'Instructor', f'{IMS_LIS}/membership#Learner'
        ])
        assert r1.codegrade_role_name == 'Teacher'
        assert r2.codegrade_role_name == 'Student'
        # IMS_LIS prefix should be removed
        assert r2.stripped_name == 'Learner'
        assert 'Teacher' in repr(r1)

    with describe('Unknown roles should be skipped'):
        roles = ContextRole.parse_roles([
            'Instructor', f'{IMS_LIS}/membership#No_Role'
        ])
        assert len(roles) == 1
        assert roles[0].codegrade_role_name == 'Teacher'

    with describe('unmapped roles should only return non mapped course roles'):
        roles = ContextRole.get_unmapped_roles([
            'Instructor',  # should not be included
            f'{IMS_LIS}/membership/Instructor#TeachingAssistant',  # also not
            f'{IMS_LIS}/membership/Instructor#SuperTA',  # Should be included
            'Base Role',  # Should be included
            # Is not a context role, not included
            f'{IMS_LIS}/namespace/Role_1_23',
        ])

        assert len(roles) == 2
        assert all(r.codegrade_role_name is None for r in roles)
        r1, r2 = roles
        assert r1.stripped_name == 'Instructor#SuperTA'
        assert r1.full_name == f'{IMS_LIS}/membership/Instructor#SuperTA'
        assert r2.full_name == roles[1].stripped_name == 'Base Role'


def test_system_roles(describe):
    with describe('Should parse roles'):
        r1, r2, r3 = SystemRole.parse_roles([
            # Bare roles are never seen as System roles!
            'SysAdmin',
            f'{IMS_LIS}/institution/person#ProspectiveStudent',
            f'{IMS_LIS}/institution/person#None',
            f'{IMS_LIS}/institution/person#SysAdmin',
        ])

        assert r1.codegrade_role_name == 'Student'
        assert r2.codegrade_role_name == 'Nobody'
        assert r3.codegrade_role_name == 'Staff'

    with describe('Can never map to an admin'):
        # Can use students
        assert SystemRole.codegrade_role_name_used('Student')

        assert not SystemRole.codegrade_role_name_used('Admin')
