import abc
import typing as t

from typing_extensions import Final

T_ROLE = t.TypeVar('T_ROLE', bound='AbstractRole[str]')
IMS_LIS: Final = 'http://purl.imsglobal.org/vocab/lis/v2'

T = t.TypeVar('T')


class AbstractRole(abc.ABC, t.Generic[T]):
    _LOOKUP: t.Mapping[str, t.Set[str]]

    def __init__(self, *, name: str, codegrade_role_name: T) -> None:
        self.name = name
        self.codegrade_role_name = codegrade_role_name

    @classmethod
    def parse(cls: t.Type[T_ROLE], role_str: str) -> t.Optional[T_ROLE]:
        for key, values in cls._LOOKUP.items():
            if role_str in values:
                return cls(name=role_str, codegrade_role_name=key)
        return None

    @classmethod
    def parse_roles(cls: t.Type[T_ROLE], roles: t.List[str]) -> t.List[T_ROLE]:
        return [role for role in map(cls.parse, roles) if role is not None]

    @classmethod
    def codegrade_role_name_used(cls, name: str) -> bool:
        """Is the given name used for any known LTI role as CodeGrade role
            name.

        This is true if there is any role ``l`` for which
        ``l.codegrade_role_name == name``.

        :param name: The CodeGrade role name to check.
        """
        return name in cls._LOOKUP

    def __repr__(self) -> str:
        return '{0}.{1}(name={2!r}, codegrade_role_name={3!r})'.format(
            self.__class__.__module__,
            self.__class__,
            self.name,
            self.codegrade_role_name,
        )


class ContextRole(AbstractRole[T], t.Generic[T]):
    _BASE = f'{IMS_LIS}/membership'

    _LOOKUP = {
        'TA': {f'{_BASE}/Instructor#TeachingAssistant'},
        'Teacher':
            {
                'Instructor',
                'Administrator',
                f'{_BASE}#Instructor',
                f'{_BASE}#Administrator',
            },
        'Student':
            {
                'Learner',
                'Member',
                f'{_BASE}#Learner',
                f'{_BASE}#Member',
            },
        'Designer': {
            'ContentDeveloper',
            f'{_BASE}#ContentDeveloper',
        },
        'Observer': {
            f'{_BASE}#Mentor',
            'Mentor',
        },
    }

    @classmethod
    def get_umapped_roles(
        cls: t.Type['ContextRole[None]'], roles: t.Sequence[str]
    ) -> t.Sequence['ContextRole[None]']:
        res = []
        for role in roles:
            if ContextRole[str].parse(role) is not None:
                continue
            elif role.startswith(cls._BASE):
                res.append(
                    cls(
                        name=role[len(cls._BASE) + 1:],
                        codegrade_role_name=None,
                    )
                )
            elif not role.startswith(IMS_LIS):
                # Bare roles should also be recognized as course roles
                # according to the LTI 1.3 spec.
                # https://www.imsglobal.org/spec/lti/v1p3/#lis-vocabulary-for-context-roles
                res.append(cls(name=role, codegrade_role_name=None))

        return res


class SystemRole(AbstractRole[str]):
    _LOOKUP = {
        'Staff':
            {
                f'{IMS_LIS}/system/person#Administrator',
                f'{IMS_LIS}/system/person#SysAdmin',
                f'{IMS_LIS}/institution/person#SysAdmin',
                f'{IMS_LIS}/institution/person#Faculty',
                f'{IMS_LIS}/institution/person#Staff',
                f'{IMS_LIS}/institution/person#Instructor',
            },
        'Student':
            {
                f'{IMS_LIS}/system/person#User',
                f'{IMS_LIS}/institution/person#Student',
                f'{IMS_LIS}/institution/person#Learner',
                f'{IMS_LIS}/institution/person#Member',
                f'{IMS_LIS}/institution/person#ProspectiveStudent',
            },
        'Nobody':
            {
                f'{IMS_LIS}/system/person#None',
                f'{IMS_LIS}/institution/person#None',
                f'{IMS_LIS}/institution/person#Other',
            },
    }
